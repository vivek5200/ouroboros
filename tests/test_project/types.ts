/**
 * Test Project - Type Definitions
 */

export interface User {
    id: string;
    username: string;
    email: string;
    createdAt: Date;
}

export interface AuthToken {
    token: string;
    expiresAt: Date;
}
