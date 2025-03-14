/**
 * Base model with common functionality for all AgentOS models
 */
const mongoose = require('mongoose');
const mongooseDelete = require('mongoose-delete');
const mongoosePaginate = require('mongoose-paginate-v2');

/**
 * Create a base schema with common fields and plugins
 * @param {Object} definition - Schema definition object
 * @param {Object} options - Schema options
 * @returns {mongoose.Schema} Mongoose schema with common plugins
 */
function createBaseSchema(definition, options = {}) {
  // Add common fields to all schemas
  const baseDefinition = {
    ...definition,
    createdBy: {
      type: String,
      required: false
    },
    updatedBy: {
      type: String,
      required: false
    }
  };

  // Create schema with timestamps
  const schema = new mongoose.Schema(baseDefinition, {
    timestamps: true,
    ...options
  });

  // Add common plugins
  schema.plugin(mongooseDelete, { 
    deletedAt: true,
    deletedBy: true,
    overrideMethods: true 
  });
  
  schema.plugin(mongoosePaginate);

  return schema;
}

module.exports = {
  createBaseSchema
};
