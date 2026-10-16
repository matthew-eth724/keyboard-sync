// server/tests/encryption.test.ts
import { EncryptionService } from '../src/encryption';

describe('EncryptionService', () => {
  let encryptionService: EncryptionService;

  beforeEach(() => {
    encryptionService = new EncryptionService();
  });

  describe('encrypt', () => {
    it('should encrypt and decrypt a message correctly', () => {
      const message = { type: 'key', key: 'a', timestamp: Date.now() };
      const encrypted = encryptionService.encrypt(message);
      const decrypted = encryptionService.decrypt(encrypted);

      expect(decrypted).toEqual(message);
    });

    it('should encrypt different messages to different strings', () => {
      const message1 = { type: 'key', key: 'a' };
      const message2 = { type: 'key', key: 'b' };

      const encrypted1 = encryptionService.encrypt(message1);
      const encrypted2 = encryptionService.encrypt(message2);

      expect(encrypted1).not.toBe(encrypted2);
    });
  });

  describe('decrypt', () => {
    it('should return null for invalid encrypted data', () => {
      const result = encryptionService.decrypt('invalid-data');
      expect(result).toBeNull();
    });
  });
});
