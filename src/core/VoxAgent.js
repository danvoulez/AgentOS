/**
 * VoxAgent - Core AI Agent for AgentOS
 * Orchestrates system-wide operations and decision making
 */

const Memory = require('./Memory');

class VoxAgent {
    constructor() {
        this.modules = new Map();
        this.eventBus = null;
        this.mlModels = new Map();
        this.memory = Memory;
        this.state = {
            isInitialized: false,
            activeProcesses: new Set(),
            systemHealth: 'nominal'
        };
    }

    async initialize(mongoConnection) {
        try {
            // Initialize core systems
            await this.memory.initialize(mongoConnection);
            await this.initializeEventBus();
            await this.initializeMLModels();
            await this.initializeModules();
            
            // Create system entity in memory
            this.memory.updateEntityProfile('vox', 'system', {
                name: 'VoxAgent',
                startTime: Date.now(),
                version: '1.0.0'
            });
            
            this.state.isInitialized = true;
            console.log('VoxAgent initialized successfully');
        } catch (error) {
            console.error('VoxAgent initialization failed:', error);
            throw error;
        }
    }

    async initializeEventBus() {
        // Initialize Kafka/RabbitMQ connection
        // Will be implemented based on chosen message queue system
    }

    async initializeMLModels() {
        // Load ML models for:
        // - Face recognition
        // - Natural language processing
        // - Predictive analytics
    }

    async initializeModules() {
        // Initialize core system modules:
        // - ERP
        // - CRM
        // - Media Processing
        // - Banking
    }

    async processEvent(event) {
        // Process incoming system events and make decisions
        const { type, data, source = 'system', sourceId = 'system' } = event;
        
        // Record event in memory
        this.memory.addEvent(sourceId, source, type, data);
        
        switch (type) {
            case 'FACE_DETECTED':
                await this.handleFaceDetection(data);
                break;
            case 'ORDER_RECEIVED':
                await this.handleNewOrder(data);
                break;
            case 'WHATSAPP_MESSAGE':
                await this.handleWhatsAppMessage(data);
                break;
            // Add more event handlers
            default:
                console.log(`Unhandled event type: ${type}`);
        }
    }

    async handleFaceDetection(data) {
        // Process face detection events
        const { faceId, confidence, mediaId, timestamp } = data;
        
        // Store face detection in memory
        this.memory.updateEntityProfile(faceId, 'face', {
            lastDetected: timestamp,
            detectionCount: (this.memory.getEntityProfile(faceId, 'face')?.detectionCount || 0) + 1
        });
        
        // Trigger video highlight generation if confidence is high enough
        if (confidence > 0.8) {
            // Add to processing queue
            this.memory.remember(`highlight:${mediaId}:${timestamp}`, {
                faceId,
                confidence,
                requestedAt: Date.now()
            });
            
            // This would trigger the actual processing elsewhere
        }
    }

    async handleNewOrder(data) {
        // Process new orders
        // Update inventory, notify relevant parties
    }

    async handleWhatsAppMessage(data) {
        // Process WhatsApp messages from either Baileys or Web.js clients
        const { content, sender, senderName, group, isGroup, timestamp, clientType, media, raw } = data;
        
        // Update sender profile in memory with more comprehensive data
        this.memory.updateEntityProfile(sender, 'user', {
            name: senderName,
            lastMessage: timestamp,
            messageCount: (this.memory.getEntityProfile(sender, 'user')?.messageCount || 0) + 1,
            lastSeen: Date.now(),
            lastClientType: clientType,
            hasSentMedia: !!media
        });
        
        if (isGroup) {
            // Update group context with more metadata
            this.memory.updateEntityProfile(group, 'group', {
                lastActivity: timestamp,
                messageCount: (this.memory.getEntityProfile(group, 'group')?.messageCount || 0) + 1,
                activeSenders: [
                    ...(this.memory.getEntityProfile(group, 'group')?.activeSenders || []),
                    sender
                ].filter((v, i, a) => a.indexOf(v) === i).slice(-20) // Keep unique recent senders
            });
        }
        
        // Get conversation context from memory to inform response generation
        const conversationContext = this._getConversationContext(isGroup ? group : sender, isGroup);
        
        // Generate response based on message content, context, and the client type
        const handlerName = `generateResponse${isGroup ? 'Group' : 'Direct'}`;
        if (this[handlerName]) {
            // Pass more context to the response generator
            const response = await this[handlerName](data, conversationContext);
            
            if (response) {
                // Record the response in memory
                this.memory.addEvent(
                    isGroup ? group : sender,
                    isGroup ? 'group' : 'user',
                    'RESPONSE_GENERATED',
                    { 
                        content: response, 
                        clientType, 
                        replyTo: data.id,
                        timestamp: new Date()
                    }
                );
            }
            
            return response;
        }
        
        return null;
    }
    
    /**
     * Get conversation context from memory for enhanced response generation
     * @param {String} entityId - The user or group ID
     * @param {Boolean} isGroup - Whether this is a group conversation
     * @returns {Object} Conversation context
     */
    _getConversationContext(entityId, isGroup) {
        // Get entity context from memory
        const context = this.memory.getContext(entityId, isGroup ? 'group' : 'user');
        const profile = this.memory.getEntityProfile(entityId, isGroup ? 'group' : 'user');
        
        // Get recent conversation history
        const recentHistory = context.history
            .filter(event => ['MESSAGE_RECEIVED', 'RESPONSE_GENERATED', 'RESPONSE_SENT'].includes(event.eventType))
            .slice(-20); // Get last 20 messages
        
        return {
            entityId,
            entityType: isGroup ? 'group' : 'user',
            profile,
            conversationHistory: recentHistory,
            firstInteraction: context.history.length <= 1,
            knownUser: !!profile?.name,
            lastInteraction: context.lastInteraction
        };
    }
    
    async generateResponseDirect(data, context) {
        // Enhanced response generation for direct messages
        const { content, sender, media } = data;
        
        // Extract user preferences and history from context
        const { profile, conversationHistory, firstInteraction } = context;
        
        // Check if this is a media message
        if (media) {
            return `I've received your ${media.type}. Thanks for sharing!`;
        }
        
        // Check if this is first interaction
        if (firstInteraction) {
            const name = profile?.name || 'there';
            return `Hello ${name}! I'm VoxAgent, your AI assistant. How can I help you today?`;
        }
        
        // In a real implementation, this would use NLP/LLM to generate contextual responses
        // For now, we'll just provide a simple acknowledgment
        const commonResponses = [
            "I've received your message and I'm processing it.",
            "Thanks for your message. I'm analyzing it now.",
            "I'll get back to you shortly with a response.",
            "I'm working on a response to your message."
        ];
        
        // Select a random response
        return commonResponses[Math.floor(Math.random() * commonResponses.length)];
    }
    
    async generateResponseGroup(data, context) {
        // Enhanced response generation for group messages
        const { content, sender, senderName, group } = data;
        
        // Extract group context and history
        const { profile, conversationHistory } = context;
        
        // Only respond to messages that mention the agent or specific keywords
        const isDirectMention = content.toLowerCase().includes('voxagent') || 
                               content.toLowerCase().includes('vox agent') ||
                               content.toLowerCase().includes('@vox');
        
        if (!isDirectMention) {
            // Don't respond to messages not directed at the agent
            return null;
        }
        
        // In a real implementation, this would use NLP/LLM to generate contextual responses
        // For now, just provide a simple response to the mention
        return `Hi ${senderName}, I'm here to help. What can I do for you in this group?`;
    }

    async shutdown() {
        // Graceful shutdown procedure
        this.state.isInitialized = false;
        
        // Record shutdown in memory
        this.memory.updateEntityProfile('vox', 'system', {
            lastShutdown: Date.now(),
            shutdownReason: 'manual'
        });
        
        // Perform memory cleanup
        await this.memory.cleanup();
        
        // Cleanup other resources
        console.log('VoxAgent shutdown complete');
    }
}

module.exports = VoxAgent;
