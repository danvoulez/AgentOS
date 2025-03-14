/**
 * Configuration manager for AgentOS
 * Loads and provides access to configuration based on environment
 */
const fs = require('fs');
const path = require('path');

class ConfigManager {
  constructor() {
    this.config = {};
    this.loadConfig();
  }

  /**
   * Load configuration based on current environment
   */
  loadConfig() {
    try {
      // Determine environment
      const env = process.env.NODE_ENV || 'development';
      
      // Default config path
      let configPath = path.join(__dirname, 'environments', 'default.json');
      
      // Try to load environment-specific config
      const envConfigPath = path.join(__dirname, 'environments', `${env}.json`);
      
      // Load default config
      if (fs.existsSync(configPath)) {
        const defaultConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        this.config = defaultConfig;
      }
      
      // Override with environment-specific config if it exists
      if (fs.existsSync(envConfigPath)) {
        const envConfig = JSON.parse(fs.readFileSync(envConfigPath, 'utf8'));
        this.config = { ...this.config, ...envConfig };
      }
      
      // Override with environment variables
      this.applyEnvOverrides();
      
      console.log(`Configuration loaded for environment: ${env}`);
    } catch (error) {
      console.error('Error loading configuration:', error);
      throw error;
    }
  }

  /**
   * Apply environment variable overrides to config
   * Environment variables prefixed with CONFIG_ will override config values
   * e.g. CONFIG_DATABASE_URL will override config.database.url
   */
  applyEnvOverrides() {
    Object.keys(process.env).forEach(key => {
      if (key.startsWith('CONFIG_')) {
        const configPath = key.substring(7).toLowerCase().split('_');
        let current = this.config;
        
        // Navigate to the nested property
        for (let i = 0; i < configPath.length - 1; i++) {
          const part = configPath[i];
          if (!current[part]) {
            current[part] = {};
          }
          current = current[part];
        }
        
        // Set the value
        current[configPath[configPath.length - 1]] = process.env[key];
      }
    });
  }

  /**
   * Get a configuration value
   * @param {string} key - Dot-notation path to config value
   * @param {any} defaultValue - Default value if key not found
   * @returns {any} Configuration value
   */
  get(key, defaultValue = null) {
    const parts = key.split('.');
    let current = this.config;
    
    for (const part of parts) {
      if (current === undefined || current === null || !Object.prototype.hasOwnProperty.call(current, part)) {
        return defaultValue;
      }
      current = current[part];
    }
    
    return current;
  }

  /**
   * Get all configuration
   * @returns {Object} Complete configuration object
   */
  getAll() {
    return { ...this.config };
  }
}

// Create singleton instance
const configManager = new ConfigManager();

module.exports = configManager;
