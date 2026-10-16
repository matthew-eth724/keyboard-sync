// mobile/src/components/PairingScreen.tsx
import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator } from 'react-native';
import { WebSocketService } from '../services/websocketService';
import { ApiService } from '../services/apiService';
import { CONSTANTS } from '@/shared/constants';

export const PairingScreen: React.FC = () => {
  const [pairingCode, setPairingCode] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<string>('');
  const [role, setRole] = useState<'pc' | 'mobile' | 'viewer'>('viewer');

  const webSocketService = new WebSocketService();
  const apiService = new ApiService();

  useEffect(() => {
    return () => {
      webSocketService.disconnect();
    };
  }, []);

  const generatePairingCode = async () => {
    setIsGenerating(true);
    const response = await apiService.generatePairingCode();
    
    if (response.success && response.data) {
      const code = response.data.pairingCode;
      setPairingCode(code);
      setConnectionStatus(`Pairing code generated: ${code}`);
      
      // Auto-connect for mobile role
      if (role === 'mobile') {
        webSocketService.connect('mobile', code);
      }
    } else {
      setConnectionStatus('Failed to generate pairing code');
    }
    
    setIsGenerating(false);
  };

  const selectRole = (selectedRole: 'pc' | 'mobile') => {
    setRole(selectedRole);
    if (pairingCode) {
      webSocketService.connect(selectedRole, pairingCode);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Keyboard Sync - Phase 1</Text>
      
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Role Selection</Text>
        <View style={styles.roleButtons}>
          <TouchableOpacity 
            style={[styles.roleButton, role === 'pc' && styles.roleButtonActive]}
            onPress={() => selectRole('pc')}
          >
            <Text style={styles.roleButtonText}>PC</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            style={[styles.roleButton, role === 'mobile' && styles.roleButtonActive]}
            onPress={() => selectRole('mobile')}
          >
            <Text style={styles.roleButtonText}>Mobile</Text>
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Pairing Code</Text>
        <TouchableOpacity 
          style={styles.generateButton}
          onPress={generatePairingCode}
          disabled={isGenerating}
        >
          {isGenerating ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.generateButtonText}>Generate Pairing Code</Text>
          )}
        </TouchableOpacity>
        
        {pairingCode && (
          <View style={styles.codeDisplay}>
            <Text style={styles.codeText}>{pairingCode}</Text>
            <Text style={styles.codeInstructions}>
              Share this code with the other device and use ?pairingCode={pairingCode}
            </Text>
          </View>
        )}
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Connection Status</Text>
        <Text style={styles.statusText}>{connectionStatus}</Text>
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
    fontSize: 24,
    fontWeight: 'bold',
    color: '#eee',
    marginTop: 40,
    marginBottom: 30,
    textAlign: 'center',
  },
  section: {
    marginBottom: 25,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#eee',
    marginBottom: 15,
  },
  roleButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  roleButton: {
    flex: 1,
    padding: 15,
    backgroundColor: '#2a2a2a',
    borderRadius: 8,
    marginHorizontal: 5,
    alignItems: 'center',
  },
  roleButtonActive: {
    backgroundColor: '#4a9',
  },
  roleButtonText: {
    color: '#eee',
    fontSize: 16,
    fontWeight: '600',
  },
  generateButton: {
    backgroundColor: '#4a9',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  generateButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  codeDisplay: {
    backgroundColor: '#2a2a2a',
    padding: 20,
    borderRadius: 8,
    marginTop: 15,
    alignItems: 'center',
  },
  codeText: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#4a9',
    marginBottom: 10,
    letterSpacing: 3,
  },
  codeInstructions: {
    color: '#aaa',
    textAlign: 'center',
    fontSize: 14,
  },
  statusText: {
    color: '#4a9',
    textAlign: 'center',
    fontSize: 16,
  },
});
