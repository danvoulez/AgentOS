/**
 * Person model for people-service
 */
const mongoose = require('mongoose');
const { createBaseSchema } = require('../../../common/models/baseModel');

// Bank account sub-schema
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

// Create person schema using base schema
const personSchema = createBaseSchema({
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
        lowercase: true,
        match: [/^\w+([.-]?\w+)*@\w+([.-]?\w+)*(\.\w{2,3})+$/, 'Please provide a valid email address']
    },
    phone: {
        type: String,
        trim: true
    },
    address: {
        street: String,
        city: String,
        state: String,
        zipCode: String,
        country: String
    },
    dateOfBirth: Date,
    roles: {
        type: [String],
        enum: ['customer', 'courier', 'admin', 'manager'],
        default: ['customer']
    },
    profileImage: String,
    bankAccount: bankAccountSchema,
    preferences: {
        type: Map,
        of: mongoose.Schema.Types.Mixed,
        default: {}
    },
    lastLogin: Date,
    status: {
        type: String,
        enum: ['active', 'inactive', 'suspended'],
        default: 'active'
    },
    verificationStatus: {
        email: {
            type: Boolean,
            default: false
        },
        phone: {
            type: Boolean,
            default: false
        },
        documents: {
            type: Boolean,
            default: false
        }
    }
});

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

personSchema.methods.updateBankBalance = function(amount, type, description) {
    if (!this.bankAccount) {
        this.bankAccount = {
            balance: 0,
            transactions: []
        };
    }
    
    const transaction = {
        type,
        amount,
        description,
        date: new Date()
    };
    
    this.bankAccount.transactions.push(transaction);
    
    if (type === 'credit') {
        this.bankAccount.balance += amount;
    } else if (type === 'debit') {
        this.bankAccount.balance -= amount;
    }
    
    return this.save();
};

// Statics
personSchema.statics.findByRole = function(role) {
    return this.find({ roles: role });
};

const Person = mongoose.model('Person', personSchema);

module.exports = Person;
