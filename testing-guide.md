# Testing Guide

## Overview

This document provides comprehensive testing guidance for the keyboard-sync project, covering automated unit tests, integration tests, and manual testing procedures for all components.

## Project Structure Testing

### 1. Server Testing (`server/`)

**Framework**: Jest (configured in `server/package.json`)

**Test Directory**: `server/tests/` (currently empty - tests need to be implemented)

**Setup Commands**:

```bash
# Run all server tests
cd server
npm test

# Run tests with coverage
npm run test-cov  # Requires additional scripts

# Run tests in CI mode
cd server && npm run test-ci

# Run Jest with verbose output
cd server && npm test -- --verbose
```

**Key Test Areas**:

- **WebSocket functionality**:
  - Message encryption/decryption
  - Connection lifecycle management
  - Room-based pairing system
  - Message routing and processing

- **API endpoints**:
  - Pairing code generation
  - Keyboard toggle operations
  - Clipboard operations
  - Health monitoring endpoints

- **Encryption service**:
  - AES-256-GCM encryption testing
  - Key generation and rotation
  - Message security validation

**Test Structure**:

```typescript
// Example test file structure
// server/tests/server.test.ts

import { Server } from '../src/server';
import { WebSocket } from 'ws';

describe('WebSocket Server', () => {
  let server: Server;

  beforeEach(() => {
    server = new Server();
  });

  afterEach(() => {
    server.close();
  });

  test('should handle incoming connections', async () => {
    // Test WebSocket connection establishment
  });

  test('should encrypt messages', () => {
    // Test AES-256-GCM encryption
  });
});
```

### 2. Shared Infrastructure Testing (`shared/`)

**TypeScript Type Definitions**: `shared/src/types.ts`

**Test Coverage**:

- Type validation
- Interface compliance
- Utility function testing
- Constants verification

### 3. Mobile App Testing (`mobile/`)

**Framework**: React Native with Detox or Jest

**Test Commands**:

```bash
# Run mobile tests
cd mobile
npm test

# Run iOS tests (requires Xcode)
npm run test:ios

# Run Android tests (requires Android Studio)
npm run test:android
```

**Key Test Areas**:

- **Pairing screen functionality**:
  - Pairing code generation
  - QR code scanning
  - Code validation

- **Keyboard interface**:
  - Virtual keyboard input
  - Keyboard toggle functionality
  - Remote keyboard forwarding

- **Clipboard operations**:
  - Clipboard read/write operations
  - Cross-platform clipboard sync
  - Data persistence

### 4. Desktop App Testing (`desktop/`)

**Framework**: Jest + Electron

**Test Commands**:

```bash
# Run desktop tests
cd desktop
npm test

# Run renderer tests (frontend)
npm run test:renderer

# Run main process tests (backend)
npm run test:main
```

**Key Test Areas**:

- **Electron functionality**:
  - App startup and shutdown
  - System tray integration
  - Native IPC communication

- **UI components**:
  - Keyboard toggle controls
  - Clipboard receiver interface
  - Connection status monitoring

- **API integration**:
  - Server communication
  - Authentication flows
  - Data synchronization

## Integration Testing

### Cross-Platform Sync Testing

**End-to-End Workflow**:

1. **Setup Phase**:
   - Start server: `cd server && npm start`
   - Launch mobile app: `cd mobile && npm start`
   - Launch desktop app: `cd desktop && npm start`

2. **Test Scenarios**:

   - **Pairing Workflow**:
     - Generate pairing code on server
     - Enter code on mobile device
     - Connect desktop to same pairing code
     - Verify all devices are synchronized

   - **Keyboard Sync Test**:
     - Type on mobile device
     - Verify keyboard forwarding to desktop
     - Test keyboard toggle controls
     - Verify connection status indicators

   - **Clipboard Sync Test**:
     - Copy content on mobile device
     - Verify clipboard sync to desktop
     - Test clipboard receiver interface
     - Validate data integrity

### Automation Tools

**Test Automation Script** (`test/automation.sh`):

```bash
#!/bin/bash
# Automated integration testing script

set -e

echo "Starting integration tests..."

# Start server in background
cd server
npm start &
SERVER_PID=$!
sleep 3

# Run server tests
npm test

# Start mobile simulator (if available)
# cd mobile
# npm run test:ios &
# MOBILE_PID=$!

# Start desktop test environment
# cd desktop
# npm run test:main &
# DESKTOP_PID=$!

# Wait for tests to complete
# wait $MOBILE_PID $DESKTOP_PID

# Kill server
kill $SERVER_PID

echo "Integration tests completed successfully"
```

## Manual Testing Procedures

### Quick Start Manual Testing

**Prerequisites**:
- Node.js 18+ installed
- TypeScript compiler
- Expo CLI (for mobile)
- Electron (for desktop)

**Manual Test Checklist**:

1. **Server Manual Tests**:
   - [ ] Server starts successfully on port 3000
   - [ ] WebSocket connections establish correctly
   - [ ] Pairing code generation works
   - [ ] API endpoints respond as expected
   - [ ] Health check endpoint returns 200

2. **Mobile Manual Tests**:
   - [ ] App launches on iOS/Android simulators
   - [ ] Pairing code generation works
   - [ ] Virtual keyboard interface functions
   - [ ] Clipboard operations work
   - [ ] WebSocket connection maintains

3. **Desktop Manual Tests**:
   - [ ] Electron app launches successfully
   - [ ] System tray integration works
   - [ ] Keyboard toggle controls function
   - [ ] Clipboard receiver displays data
   - [ ] Server API integration works

4. **Integration Manual Tests**:
   - [ ] Cross-device pairing works
   - [ ] Keyboard sync functions end-to-end
   - [ ] Clipboard sync works end-to-end
   - [ ] Connection resilience under load
   - [ ] Encryption security maintained

### Testing Workflow

**Development Workflow**:

```bash
# 1. Initial setup
cd keyboard-sync
npm install
cd shared && npm run build
cd server && npm install
cd mobile && npm install
cd desktop && npm install

# 2. Development and testing
cd server
npm test           # Run unit tests
npm start          # Start server for manual testing

# 3. Integration testing
cd ../..
./scripts/integration-test.sh

# 4. Final verification
cd server && npm run test-cov
```

## CI/CD Testing

### GitHub Actions Configuration

**Test Workflow** (`.github/workflows/test.yml`):

```yaml
name: Test Suite

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [18.x, 20.x]
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: ${{ matrix.node-version }}
        cache: 'npm'
    
    - name: Install dependencies
      run: npm install
    
    -: Run server tests
      run: |
        cd server
        npm install
        npm test
    
    - name: Run mobile tests
      run: |
        cd mobile
        npm install
        npm test
    
    - name: Run desktop tests
      run: |
        cd desktop
        npm install
        npm test
    
    - name: Generate test coverage
      run: |
        cd server
        npm run test-cov
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./server/coverage/lcov.info
        flags: server
```

### Test Coverage Reporting

**Coverage Metrics**:

- **Unit Test Coverage**: Target 80%+
- **Integration Test Coverage**: Target 70%+
- **Cross-Platform Coverage**: Target 90%+

**Coverage Tools**:

- **Server**: Jest with Istanbul
- **Mobile**: Jest/React Native Testing Library
- **Desktop**: Jest + Electron

**Coverage Reports**:

```bash
# Server coverage report
cd server
npm run test-cov
# Generates ./server/coverage/html

cd server
npm run test-ci
# Generates ./server/coverage/lcov.info
```

## Testing Best Practices

### Code Quality Standards

1. **Type Safety**:
   - Use TypeScript strict mode
   - Validate all API contracts
   - Test edge cases with TypeScript types

2. **Error Handling**:
   - Test all error scenarios
   - Validate error messages
   - Test connection resilience

3. **Security Testing**:
   - Validate encryption implementation
   - Test authentication flows
   - Verify data integrity

4. **Performance Testing**:
   - Test message throughput
   - Test connection handling
   - Test memory usage

### Test Organization

**Directory Structure**:

```
keyboard-sync/
├── server/
│   ├── src/                    # Server source code
│   ├── tests/                  # Unit tests
│   └── __mocks__/              # Jest mocks
├── mobile/
│   ├── src/                    # Mobile source code
│   └── __tests__/              # React Native tests
├── desktop/
│   ├── src/                    # Desktop source code
│   └── __tests__/              # Electron tests
├── shared/
│   ├── src/                    # Shared types and utils
│   └── __tests__/              # Shared tests
└── test/                      # Integration tests
    ├── integration.sh
    ├── e2e/                   # End-to-end tests
    └── manual/                # Manual testing guides
```

### Test Maintenance

**Regular Maintenance Tasks**:

1. **Weekly Review**:
   - Check test coverage reports
   - Update test data
   - Remove deprecated tests

2. **Monthly Review**:
   - Refactor flaky tests
   - Add missing edge cases
   - Update test documentation

3. **Quarterly Review**:
   - Complete test suite audit
   - Update testing strategy
   - Review testing ROI

## Troubleshooting

### Common Test Issues

**Issue 1: Jest not running**

**Symptoms**:
- `npm test` hangs or fails
- No test output

**Solution**:
```bash
# Clear Jest cache
cd server
npm test -- --clearCache

# Check Jest configuration
cat server/jest.config.js

# Verify dependencies
cd server && npm list jest
```

**Issue 2: TypeScript compilation errors**

**Symptoms**:
- TypeScript errors in tests
- Cannot run tests

**Solution**:
```bash
# Build shared types
cd shared && npm run build

# Reinstall server dependencies
cd server
rm -rf node_modules package-lock.json
npm install

# Check TypeScript configuration
cat server/tsconfig.json
```

**Issue 3: Cross-platform compatibility**

**Symptoms**:
- Tests pass on one platform but not another
- Environment-specific failures

**Solution**:
```bash
# Use platform-specific test scripts
cd server
npm run test:linux    # or test:macos, test:windows

# Check environment variables
cat server/.env.test
```

### Test Recovery

**After Test Failures**:

1. **Check recent changes**:
   ```bash
   git diff HEAD~1 -- tests/
   git log --oneline -10
   ```

2. **Restore test state**:
   ```bash
   # If tests were broken by changes
   git checkout HEAD -- tests/

   # Or reset to working directory
   git reset HEAD -- tests/
   ```

3. **Recreate failing tests**:
   ```bash
   # After fixing issues, recreate tests
cd server
npm test -- --watch
```

## Testing Metrics

### Success Criteria

**Automated Tests**:
- **Unit Test Coverage**: 80%+
- **Integration Test Coverage**: 70%+
- **Test Execution Time**: < 5 minutes per full suite
- **Test Reliability**: < 5% flaky rate

**Manual Testing**:
- **Feature Coverage**: 100%
- **Cross-Platform Compatibility**: 100%
- **User Experience**: Subjective rating > 4/5

### Performance Benchmarks

**Server Performance**:
- **Connection Establishment**: < 100ms
- **Message Latency**: < 50ms
- **Throughput**: 1000+ messages/second

**Mobile Performance**:
- **App Startup**: < 3 seconds
- **Keyboard Response**: < 50ms
- **Memory Usage**: < 100MB

**Desktop Performance**:
- **App Startup**: < 5 seconds
- **UI Responsiveness**: < 16ms (60fps)
- **Memory Usage**: < 200MB

## Conclusion

The testing strategy combines automated unit tests, integration tests, and manual testing to ensure comprehensive coverage of the keyboard-sync application. By following this testing guide, developers can maintain high code quality and ensure reliable cross-platform functionality.

**Next Steps**:

1. Implement the missing test files
2. Set up CI/CD pipeline
3. Establish regular test maintenance routines
4. Expand test coverage based on priority features

---

_Last Updated: October 16, 2026_
_Contact: Development Team_
