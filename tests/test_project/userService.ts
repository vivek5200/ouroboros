/**
 * Test Project - User Service (TypeScript)
 */

import { User } from './types';

export class UserService {
    private users: Map<string, User>;

    constructor() {
        this.users = new Map();
    }

    async createUser(username: string, email: string): Promise<User> {
        const user: User = {
            id: generateId(),
            username,
            email,
            createdAt: new Date()
        };
        
        this.users.set(user.id, user);
        return user;
    }

    async getUser(id: string): Promise<User | null> {
        return this.users.get(id) || null;
    }

    async deleteUser(id: string): Promise<boolean> {
        return this.users.delete(id);
    }
}

function generateId(): string {
    return Math.random().toString(36).substring(7);
}

export default UserService;
