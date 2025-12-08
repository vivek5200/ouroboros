// Test Project - Main Entry Point (JavaScript)

const { UserService } = require('./userService');
const { AuthService } = require('./auth');

class Application {
    constructor() {
        this.userService = new UserService();
        this.authService = new AuthService();
    }

    async start() {
        console.log('Application started');
    }

    async shutdown() {
        console.log('Application shutting down');
    }
}

module.exports = { Application };
