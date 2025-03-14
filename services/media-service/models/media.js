/**
 * Media model for media-service
 */
const mongoose = require('mongoose');
const { createBaseSchema } = require('../../../common/models/baseModel');

// Face detection sub-schema
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

// Highlight sub-schema
const highlightSchema = new mongoose.Schema({
    personId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Person'
    },
    start: {
        type: Number,
        required: true
    },
    end: {
        type: Number,
        required: true
    },
    title: {
        type: String,
        required: true
    },
    status: {
        type: String,
        enum: ['pending', 'processing', 'completed', 'failed'],
        default: 'pending'
    },
    processedUrl: String,
    createdAt: {
        type: Date,
        default: Date.now
    }
});

// Create media schema using base schema
const mediaSchema = createBaseSchema({
    title: {
        type: String,
        required: true,
        trim: true
    },
    description: {
        type: String,
        trim: true
    },
    type: {
        type: String,
        enum: ['image', 'video', 'audio', 'document'],
        required: true
    },
    url: {
        type: String,
        required: true
    },
    thumbnailUrl: String,
    duration: Number, // For video/audio in seconds
    size: Number, // In bytes
    format: String, // File format (mp4, jpg, etc.)
    resolution: {
        width: Number,
        height: Number
    },
    metadata: {
        type: Map,
        of: mongoose.Schema.Types.Mixed,
        default: {}
    },
    tags: [String],
    visibility: {
        type: String,
        enum: ['public', 'private', 'restricted'],
        default: 'private'
    },
    owner: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Person',
        required: true
    },
    accessList: [{
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Person'
    }],
    faceDetections: [faceDetectionSchema],
    highlights: [highlightSchema],
    processingStatus: {
        type: String,
        enum: ['pending', 'processing', 'completed', 'failed'],
        default: 'pending'
    }
});

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
    }
    
    return this.save();
};

// Statics
mediaSchema.statics.findByPerson = function(personId) {
    return this.find({
        $or: [
            { owner: personId },
            { accessList: personId },
            { 'faceDetections.personId': personId }
        ]
    });
};

mediaSchema.statics.findPendingHighlights = function() {
    return this.find({ 'highlights.status': 'pending' });
};

const Media = mongoose.model('Media', mediaSchema);

module.exports = Media;
