// mobile/src/App.tsx
import React, { useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { PairingScreen } from './components/PairingScreen';
import { KeyboardInterface } from './components/KeyboardInterface';

const Stack = createStackNavigator();

export default function App() {
  const [isPaired, setIsPaired] = useState(false);

  return (
    <NavigationContainer>
      <Stack.Navigator>
        {isPaired ? (
          <Stack.Screen
            name="KeyboardInterface"
            component={KeyboardInterface}
            options={{ headerShown: false }}
          />
        ) : (
          <Stack.Screen
            name="Pairing"
            component={PairingScreen}
            options={{ headerShown: false }}
          />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
