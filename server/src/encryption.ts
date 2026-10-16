// server/src/encryption.ts
import crypto from 'crypto';

export class EncryptionService {
  private readonly algorithm = 'aes-256-gcm';
  private readonly key: Buffer;

  constructor(key?: Buffer) {
    this.key = key || crypto.randomBytes(32);
  }

  encrypt(message: any): string {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv(this.algorithm, this.key, iv);
    
    const jsonString = JSON.stringify(message);
    let encrypted = cipher.update(jsonString, 'utf8', 'binary');
    encrypted += cipher.final('binary');
    
    const tag = cipher.getAuthTag();
    
    const buffer = Buffer.concat([iv, tag, Buffer.from(encrypted, 'binary')]);
    return buffer.toString('base64');
  }

  decrypt(encryptedData: string): any {
    try {
      const buffer = Buffer.from(encryptedData, 'base64');
      const iv = buffer.slice(0, 16);
      const tag = buffer.slice(16, 32);
      const encrypted = buffer.slice(32);
      
      const decipher = crypto.createDecipheriv(this.algorithm, this.key, iv);
      decipher.setAuthTag(tag);
      
      let decrypted = decipher.update(encrypted);
      decrypted = Buffer.concat([decrypted, decipher.final()]);
      
      return JSON.parse(decrypted.toString('utf8'));
    } catch (error) {
      console.error('Decryption error:', error);
      return null;
    }
  }

  getKey(): Buffer {
    return this.key;
  }
}
