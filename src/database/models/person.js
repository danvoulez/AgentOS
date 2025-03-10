const mongoose = require('mongoose');
const mongooseDelete = require('mongoose-delete');
const mongoosePaginate = require('mongoose-paginate-v2');

const bankAccountSchema = new mongoose.Schema({
    balance: {
        type: mongoose.Types.Decimal128,
        default: 0
    },
    transactions: [{
        type: {
            type: String,
            enum: ['credit', 'debit'],
            required: true
        },
        amount: {
            type: mongoose.Types.Decimal128,
            required: true
        },
        description: String,
        date: {
            type: Date,
            default: Date.now
        }
    }]
});

const mediaAccessSchema = new mongoose.Schema({
    videoId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Media'
    },
    timestamps: [{
        type: Date,
        default: Date.now
    }]
});

const personSchema = new mongoose.Schema({
    name: {
        type: String,
        required: true,
        trim: true
    },
    email: {
        type: String,
        required: true,
        unique: true,
        trim: true,
        lowercase: true
    },
    phone: {
        type: String,
        unique: true,
        sparse: true
    },
    roles: [{
        type: String,
        enum: ['client', 'reseller', 'employee', 'admin'],
        default: ['client']
    }],
    faceEmbedding: {
        type: Buffer,
        select: false // Only load when explicitly requested
    },
    bankAccount: bankAccountSchema,
    mediaAccess: [mediaAccessSchema],
    lastLogin: Date,
    status: {
        type: String,
        enum: ['active', 'inactive', 'suspended'],
        default: 'active'
    }
}, {
    timestamps: true,
    toJSON: { virtuals: true },
    toObject: { virtuals: true }
});

// Indexes
personSchema.index({ email: 1 });
personSchema.index({ phone: 1 });
personSchema.index({ roles: 1 });
personSchema.index({ 'bankAccount.balance': 1 });

// Plugins
personSchema.plugin(mongooseDelete, { 
    deletedAt: true,
    overrideMethods: true 
});
personSchema.plugin(mongoosePaginate);

// Methods
personSchema.methods.addRole = function(role) {
    if (!this.roles.includes(role)) {
        this.roles.push(role);
    }
    return this.save();
};

personSchema.methods.removeRole = function(role) {
    this.roles = this.roles.filter(r => r !== role);
    return this.save();
};

personSchema.methods.updateBankBalance = async function(amount, type, description) {
    const transaction = {
        type,
        amount: mongoose.Types.Decimal128.fromString(amount.toString()),
        description,
        date: new Date()
    };

    this.bankAccount.transactions.push(transaction);
    
    if (type === 'credit') {
        this.bankAccount.balance = mongoose.Types.Decimal128.fromString(
            (parseFloat(this.bankAccount.balance.toString()) + parseFloat(amount)).toString()
        );
    } else {
        this.bankAccount.balance = mongoose.Types.Decimal128.fromString(
            (parseFloat(this.bankAccount.balance.toString()) - parseFloat(amount)).toString()
        );
    }

    return this.save();
};

// Statics
personSchema.statics.findByRole = function(role) {
    return this.find({ roles: role });
};

const Person = mongoose.model('Person', personSchema);

module.exports = Person;
