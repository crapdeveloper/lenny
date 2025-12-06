import React, { useEffect, useState } from 'react';
import {
  AppShell,
  Group,
  Title,
  Text,
  Button,
  Container,
  ActionIcon,
  useMantineColorScheme,
  useComputedColorScheme,
  Avatar,
  Grid,
  Stack,
  SegmentedControl,
  Select,
} from '@mantine/core';
import MarketDashboard from './MarketDashboard';
import ChatWidget from './ChatWidget';
import ItemFilterWidget from './ItemFilterWidget';
import LocationBrowser from './LocationBrowser';
import EveIcon from './EveIcon';

function App() {
  const [message, setMessage] = useState('');
  const [character, setCharacter] = useState(null);
  const [characterId, setCharacterId] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [itemSearchValue, setItemSearchValue] = useState('');
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [orderType, setOrderType] = useState('all');
  const [resetTrigger, setResetTrigger] = useState(0);
  const [themeMode, setThemeMode] = useState(() => {
    return localStorage.getItem('lenny_theme_mode') || 'default';
  });
  const { setColorScheme } = useMantineColorScheme();
  const computedColorScheme = useComputedColorScheme('light', { getInitialValueInEffect: true });

  useEffect(() => {
    // Apply theme based on mode
    if (themeMode === 'default') {
      const osTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      setColorScheme(osTheme);
    } else {
      setColorScheme(themeMode);
    }
    localStorage.setItem('lenny_theme_mode', themeMode);
  }, [themeMode, setColorScheme]);

  useEffect(() => {
    // Check for character param in URL (simple auth handling)
    const params = new URLSearchParams(window.location.search);
    const charName = params.get('character');
    const charId = params.get('character_id');

    // Check local storage
    const storedCharacter = localStorage.getItem('lenny_character');
    const storedCharacterId = localStorage.getItem('lenny_character_id');

    if (charName) {
      setCharacter(charName);
      localStorage.setItem('lenny_character', charName);

      if (charId) {
        setCharacterId(charId);
        localStorage.setItem('lenny_character_id', charId);
      }

      // Clean URL
      window.history.replaceState({}, document.title, '/');
    } else if (storedCharacter) {
      setCharacter(storedCharacter);
      if (storedCharacterId) {
        setCharacterId(storedCharacterId);
      }
    }

    fetch('http://localhost:8000/')
      .then((res) => res.json())
      .then((data) => setMessage(data.message))
      .catch((err) => console.error(err));
  }, []);

  const handleLogin = () => {
    window.location.href = 'http://localhost:8000/auth/login';
  };

  const handleLogout = () => {
    setCharacter(null);
    setCharacterId(null);
    localStorage.removeItem('lenny_character');
    localStorage.removeItem('lenny_character_id');
  };

  const handleClearFilters = () => {
    setSelectedLocation(null);
    setSelectedItem(null);
    setSelectedGroup(null);
    setItemSearchValue('');
    setOrderType('all');
    setResetTrigger((prev) => prev + 1);
  };

  return (
    <AppShell header={{ height: 60 }} padding="md">
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Title order={3}>Lenny Dashboard</Title>
          </Group>
          <Group>
            <Select
              value={themeMode}
              onChange={setThemeMode}
              data={[
                { label: 'Default (OS)', value: 'default' },
                { label: 'Light', value: 'light' },
                { label: 'Dark', value: 'dark' },
              ]}
              style={{ width: 150 }}
              placeholder="Select theme"
              leftSection={<span style={{ fontSize: '1.2rem' }}>🎨</span>}
            />
            {character ? (
              <Group>
                <Group gap="xs">
                  {characterId && (
                    <EveIcon id={characterId} type="character" size={38} useAvatar radius="xl" />
                  )}
                  <Text>Welcome, {character}</Text>
                </Group>
                <Button onClick={handleLogin} variant="outline" color="blue">
                  Change Character
                </Button>
                <Button onClick={handleLogout} variant="light" color="red">
                  Logout
                </Button>
              </Group>
            ) : (
              <Button onClick={handleLogin} color="yellow" variant="filled" c="black">
                Login with EVE
              </Button>
            )}
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Main>
        <Container
          size="xl"
          fluid
          style={{
            height: 'calc(100vh - 120px)',
            display: 'flex',
            flexDirection: 'column',
            padding: 0,
          }}
        >
          <div
            style={{
              padding: '0.5rem 1rem',
              borderBottom: '1px solid var(--mantine-color-gray-3)',
            }}
          >
            <Text c="dimmed" size="sm">
              Backend Status: {message}
            </Text>
          </div>
          <div style={{ display: 'flex', flex: 1, gap: '1rem', padding: '1rem', minHeight: 0 }}>
            <div
              style={{
                width: '25%',
                display: 'flex',
                flexDirection: 'column',
                minHeight: 0,
                gap: '1rem',
              }}
            >
              <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
                <ItemFilterWidget
                  selectedItem={selectedItem}
                  onSelect={setSelectedItem}
                  selectedGroup={selectedGroup}
                  onSelectGroup={setSelectedGroup}
                  searchValue={itemSearchValue}
                  onSearchChange={setItemSearchValue}
                  resetTrigger={resetTrigger}
                />
              </div>
              <div style={{ flexShrink: 0 }}>
                <LocationBrowser
                  selectedLocation={selectedLocation}
                  onLocationSelect={setSelectedLocation}
                />
              </div>
              <div style={{ flexShrink: 0 }}>
                <Text fw={600} size="sm" mb="xs">
                  Order Type
                </Text>
                <SegmentedControl
                  value={orderType}
                  onChange={setOrderType}
                  data={[
                    { label: 'All', value: 'all' },
                    { label: 'Buy', value: 'buy' },
                    { label: 'Sell', value: 'sell' },
                  ]}
                  fullWidth
                  size="sm"
                />
              </div>
              <Button variant="default" onClick={handleClearFilters} size="sm" fullWidth>
                Clear All Filters
              </Button>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <MarketDashboard
                selectedItem={selectedItem}
                selectedGroup={selectedGroup}
                selectedLocation={selectedLocation}
                orderType={orderType}
                colorScheme={computedColorScheme}
                onItemSearchIconClick={(item) => {
                  // When item search icon clicked in dashboard, select item and set search value
                  setSelectedItem({ id: item.id, name: item.name });
                  setItemSearchValue(item.name);
                }}
                onLocationSearchIconClick={(location) => {
                  // When location search icon clicked in dashboard, set selected location
                  setSelectedLocation(location);
                }}
              />
            </div>
          </div>
        </Container>
        <ChatWidget characterId={characterId} />
      </AppShell.Main>
    </AppShell>
  );
}

export default App;
