import React, { useState, useCallback, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  Paper,
  Stack,
  TextInput,
  Group,
  Loader,
  Text,
  Badge,
  ScrollArea,
  ActionIcon,
  Box,
} from '@mantine/core';

const LocationBrowser = ({ selectedLocation, onLocationSelect }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const debounceTimer = useRef(null);

  // Debounced search
  useEffect(() => {
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    if (searchQuery.length < 3) {
      setResults([]);
      return;
    }

    setLoading(true);
    debounceTimer.current = setTimeout(() => {
      axios
        .get(`http://localhost:8000/api/market/locations/search`, { params: { q: searchQuery } })
        .then((res) => {
          setResults(res.data);
          setLoading(false);
        })
        .catch((err) => {
          console.error('Error searching locations:', err);
          setLoading(false);
        });
    }, 300);

    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, [searchQuery]);

  const getLocationIcon = (type) => {
    switch (type) {
      case 'region':
        return '🌍';
      case 'system':
        return '⭐';
      case 'station':
        return '🏢';
      default:
        return '📍';
    }
  };

  const getLocationColor = (type) => {
    switch (type) {
      case 'region':
        return 'blue';
      case 'system':
        return 'yellow';
      case 'station':
        return 'green';
      default:
        return 'gray';
    }
  };

  const handleLocationClick = (location) => {
    onLocationSelect(location);
    setSearchQuery('');
    setResults([]);
  };

  const handleClear = () => {
    onLocationSelect(null);
  };

  return (
    <Paper shadow="xs" p="md" radius="md">
      <Stack gap="sm">
        <Text fw={600} size="sm">
          Location
        </Text>

        {/* Active Filter Display */}
        {selectedLocation ? (
          <Group gap="xs">
            <Badge
              color={getLocationColor(selectedLocation.type)}
              variant="filled"
              size="sm"
              rightSection={
                <ActionIcon
                  size="xs"
                  color="inherit"
                  radius="xl"
                  variant="transparent"
                  onClick={handleClear}
                  style={{ cursor: 'pointer' }}
                >
                  ✕
                </ActionIcon>
              }
            >
              {getLocationIcon(selectedLocation.type)} {selectedLocation.name}
            </Badge>
          </Group>
        ) : (
          <Text size="xs" c="dimmed">
            All Regions
          </Text>
        )}

        {/* Search Input */}
        <TextInput
          placeholder="Search locations..."
          leftSection="🔍"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.currentTarget.value)}
          size="sm"
        />

        {/* Search Results */}
        {searchQuery.length >= 3 && (
          <ScrollArea h={300} type="scroll" scrollbarSize={6}>
            {loading ? (
              <Group justify="center">
                <Loader size="sm" />
              </Group>
            ) : results.length > 0 ? (
              <Stack gap={4} p={4}>
                {results.map((location) => (
                  <Group
                    key={`${location.type}-${location.id}`}
                    onClick={() => handleLocationClick(location)}
                    p={6}
                    gap={8}
                    style={{
                      cursor: 'pointer',
                      borderRadius: 4,
                      backgroundColor: 'rgba(0, 0, 0, 0.03)',
                      transition: 'background-color 0.2s',
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.08)')
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.03)')
                    }
                  >
                    <Text size="xs">{getLocationIcon(location.type)}</Text>
                    <Text size="xs" fw={500} truncate style={{ flex: 1, minWidth: 0 }}>
                      {location.name}
                    </Text>
                  </Group>
                ))}
              </Stack>
            ) : (
              <Text size="sm" c="dimmed" p="xs" ta="center">
                No locations found
              </Text>
            )}
          </ScrollArea>
        )}
      </Stack>
    </Paper>
  );
};

export default LocationBrowser;
