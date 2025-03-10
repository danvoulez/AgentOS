const mongoose = require('mongoose');
const mongooseDelete = require('mongoose-delete');
const mongoosePaginate = require('mongoose-paginate-v2');

const faceDetectionSchema = new mongoose.Schema({
    personId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Person',
        required: true
    },
    timestamp: {
        type: Date,
        required: true
    },
    confidence: {
        type: Number,
        required: true,
        min: 0,
        max: 1
    },
    boundingBox: {
        x: Number,
        y: Number,
        width: Number,
        height: Number
    }
});

const highlightSchema = new mongoose.Schema({
    personId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Person',
        required: true
    },
    start: {
        type: String,
        required: true
    },
    end: {
        type: String,
        required: true
    },
    title: String,
    status: {
        type: String,
        enum: ['pending', 'processing', 'completed', 'failed'],
        default: 'pending'
    },
    processedUrl: String
});

const mediaSchema = new mongoose.Schema({
    type: {
        type: String,
        enum: ['photo', 'video'],
        required: true
    },
    nasPath: {
        type: String,
        required: true
    },
    originalFilename: String,
    duration: Number, // For videos only
    resolution: {
        width: Number,
        height: Number
    },
    fileSize: Number,
    mimeType: String,
    faceDetections: [faceDetectionSchema],
    highlights: [highlightSchema],
    metadata: {
        event: String,
        location: String,
        tags: [String],
        customFields: mongoose.Schema.Types.Mixed
    },
    processingStatus: {
        type: String,
        enum: ['pending', 'processing', 'completed', 'failed'],
        default: 'pending'
    },
    processingError: String,
    accessControl: {
        public: {
            type: Boolean,
            default: false
        },
        allowedUsers: [{
            type: mongoose.Schema.Types.ObjectId,
            ref: 'Person'
        }]
    }
}, {
    timestamps: true,
    toJSON: { virtuals: true },
    toObject: { virtuals: true }
});

// Indexes
mediaSchema.index({ type: 1 });
mediaSchema.index({ 'faceDetections.personId': 1 });
mediaSchema.index({ processingStatus: 1 });
mediaSchema.index({ 'metadata.tags': 1 });
mediaSchema.index({ 'accessControl.allowedUsers': 1 });

// Plugins
mediaSchema.plugin(mongooseDelete, { 
    deletedAt: true,
    overrideMethods: true 
});
mediaSchema.plugin(mongoosePaginate);

// Methods
mediaSchema.methods.addFaceDetection = function(personId, timestamp, confidence, boundingBox) {
    this.faceDetections.push({
        personId,
        timestamp,
        confidence,
        boundingBox
    });
    return this.save();
};

mediaSchema.methods.createHighlight = function(personId, start, end, title) {
    const highlight = {
        personId,
        start,
        end,
        title,
        status: 'pending'
    };
    this.highlights.push(highlight);
    return this.save();
};

mediaSchema.methods.updateHighlightStatus = function(highlightId, status, processedUrl = null) {
    const highlight = this.highlights.id(highlightId);
    if (highlight) {
        highlight.status = status;
        if (processedUrl) {
            highlight.processedUrl = processedUrl;
        }
        return this.save();
    }
    throw new Error('Highlight not found');
};

// Statics
mediaSchema.statics.findByPerson = function(personId) {
    return this.find({
        'faceDetections.personId': personId
    }).sort('-createdAt');
};

mediaSchema.statics.findPendingHighlights = function() {
    return this.find({
        'highlights.status': 'pending'
    });
};

const Media = mongoose.model('Media', mediaSchema);

module.exports = Media;
