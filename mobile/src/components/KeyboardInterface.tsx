// mobile/src/components/KeyboardInterface.tsx
import React, { useState, useRef, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, TextInput } from 'react-native';
import { WebSocketService } from '../services/websocketService';
import { CONSTANTS } from '@/shared/constants';

export const KeyboardInterface: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const [lastValue, setLastValue] = useState('');
  const webSocketService = new WebSocketService();
  const connectionStatus = webSocketService.getConnectionStatus();

  useEffect(() => {
    if (connectionStatus?.isConnected) {
      const inputElement = inputRef.current;
      if (inputElement) {
        inputElement.focus();
      }
    }
  }, [connectionStatus?.isConnected]);

  const inputRef = useRef<TextInput>(null);

  const handleTextChange = (text: string) => {
    setInputText(text);
    if (text.length > lastValue.length) {
      const added = text.slice(lastValue.length);
      added.split('').forEach(char => webSocketService.sendKey(char));
    } else if (text.length < lastValue.length) {
      const diff = lastValue.length - text.length;
      for (let i = 0; i < diff; i++) {
        webSocketService.sendKey('\b');
      }
    }
    setLastValue(text);
  };

  const handleKeyPress = (key: string) => {
    if (key === 'Backspace') {
      webSocketService.sendKey('\b');
    } else if (key.length === 1) {
      webSocketService.sendKey(key);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Mobile Keyboard Interface</Text>
      
      <View style={styles.statusBar}>
        <Text style={[styles.statusText, connectionStatus?.isConnected ? styles.connected : styles.disconnected]}>
          {connectionStatus?.isConnected ? '🟢 Connected' : '🔴 Disconnected'}
        </Text>
        <Text style={styles.pairingText}>Pairing: {connectionStatus?.pairingCode}</Text>
      </View>

      <TextInput
        ref={inputRef}
        style={styles.textInput}
        value={inputText}
        onChangeText={handleTextChange}
        placeholder="Type here...
"
        autoCapitalize="none"
        autoCorrect={false}
        editable={connectionStatus?.isConnected}
      />

      <View style={styles.virtualKeyboard}>
        {CONSTANTS.UI.KEYBOARD_ROWS.map((row, rowIndex) => (
          <View key={rowIndex} style={styles.keyboardRow}>
            {row.split('').map((key) => (
              <TouchableOpacity
                key={key}
                style={styles.key}
                onPress={() => handleKeyPress(key)}
                disabled={!connectionStatus?.isConnected}
              >
                <Text style={styles.keyText}>{key}</Text>
              </TouchableOpacity>
            ))}
          </View>
        ))}
      </View>

      <View style={styles.clipboardSection}>
        <Text style={styles.clipboardTitle}>Clipboard Operations</Text>
        <TouchableOpacity
          style={[styles.clipboardButton, !connectionStatus?.isConnected && styles.clipboardButtonDisabled]}
          onPress={() => {
            if (connectionStatus?.isConnected) {
              // TODO: Add clipboard access functionality
              console.log('Clipboard access requested');
            }
          }}
        >
          <Text style={styles.clipboardButtonText}>Access PC Clipboard</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#111',
    padding: 20,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#eee',
    marginTop: 20,
    marginBottom: 20,
    textAlign: 'center',
  },
  statusBar: {
    backgroundColor: '#2a2a2a',
    padding: 15,
    borderRadius: 8,
    marginBottom: 20,
    alignItems: 'center',
  },
  statusText: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 5,
  },
  connected: {
    color: '#0a0',
  },
  disconnected: {
    color: '#a00',
  },
  pairingText: {
    color: '#aaa',
    fontSize: 14,
  },
  textInput: {
    backgroundColor: '#2a2a2a',
    color: '#eee',
    padding: 15,
    borderRadius: 8,
    fontSize: 16,
    marginBottom: 20,
    minHeight: 50,
  },
  virtualKeyboard: {
    marginBottom: 20,
  },
  keyboardRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 8,
  },
  key: {
    backgroundColor: '#2a2a2a',
    padding: 12,
    borderRadius: 6,
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 40,
    minHeight: 40,
  },
  keyText: {
    color: '#eee',
    fontSize: 16,
    fontWeight: '600',
  },
  clipboardSection: {
    marginTop: 20,
  },
  clipboardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#eee',
    marginBottom: 15,
    textAlign: 'center',
  },
  clipboardButton: {
    backgroundColor: '#4a9',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  clipboardButtonDisabled: {
    backgroundColor: '#555',
    opacity: 0.6,
  },
  clipboardButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
