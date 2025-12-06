import React, { useState, useEffect, useMemo } from 'react';
import {
  Paper,
  Title,
  TextInput,
  Stack,
  Text,
  Button,
  Loader,
  NavLink,
  ScrollArea,
  Box,
  Group,
  CloseButton,
  Badge,
} from '@mantine/core';
import axios from 'axios';
import { useDebouncedValue } from '@mantine/hooks';
import EveIcon from './EveIcon';

const FolderIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    style={{ opacity: 0.7 }}
  >
    <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 2H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z" />
  </svg>
);

function MarketGroupTree({
  groupChildrenMap,
  parentId,
  onSelectType,
  onSelectGroup,
  selectedTypeId,
  selectedGroupId,
  expandedGroups,
  toggleGroup,
  filteredGroupIds,
  injectedItems,
  isFiltering,
}) {
  const children = groupChildrenMap.get(parentId || null) || [];

  // Filter children: show all if not filtering, or only filtered ones if filtering
  const visibleChildren = isFiltering
    ? children.filter((g) => filteredGroupIds.has(g.id))
    : children; // Show all children when not filtering

  if (!visibleChildren.length) return null;

  return (
    <Box pl={parentId ? 'md' : 0}>
      {visibleChildren.map((group) => (
        <MarketGroupNode
          key={group.id}
          group={group}
          groupChildrenMap={groupChildrenMap}
          onSelectType={onSelectType}
          onSelectGroup={onSelectGroup}
          selectedTypeId={selectedTypeId}
          selectedGroupId={selectedGroupId}
          expandedGroups={expandedGroups}
          toggleGroup={toggleGroup}
          filteredGroupIds={filteredGroupIds}
          injectedItems={injectedItems}
          isFiltering={isFiltering}
        />
      ))}
    </Box>
  );
}

function MarketGroupNode({
  group,
  groupChildrenMap,
  onSelectType,
  onSelectGroup,
  selectedTypeId,
  selectedGroupId,
  expandedGroups,
  toggleGroup,
  filteredGroupIds,
  injectedItems,
  isFiltering,
}) {
  const [types, setTypes] = useState([]);
  const [loadingTypes, setLoadingTypes] = useState(false);
  const isExpanded = expandedGroups.has(group.id);

  // Determine which items to show
  const displayItems =
    isFiltering && injectedItems.has(group.id) ? injectedItems.get(group.id) : types; // When not filtering, always show types (which are loaded on demand)

  const sortedItems = useMemo(() => {
    return [...displayItems].sort((a, b) => a.name.localeCompare(b.name));
  }, [displayItems]);

  useEffect(() => {
    // Fetch types if: expanded AND has types AND (no types loaded yet) AND (not filtering OR not injected for this group)
    // In other words: fetch when expanded and we don't already have them (unless we're using injected search results)
    if (
      isExpanded &&
      group.has_types &&
      types.length === 0 &&
      (!isFiltering || !injectedItems.has(group.id))
    ) {
      setLoadingTypes(true);
      axios
        .get(`http://localhost:8000/api/market/groups/${group.id}/types?size=250`)
        .then((res) => {
          setTypes(res.data.items);
          setLoadingTypes(false);
        })
        .catch((err) => {
          console.error(`Error fetching types for group ${group.id}:`, err);
          setLoadingTypes(false);
        });
    }
    // Note: if not filtering AND this group doesn't have injected items, show the regular types if they've been loaded
  }, [isExpanded, group.has_types, group.id, types.length, isFiltering, injectedItems]);

  const handleGroupChange = () => {
    toggleGroup(group.id);
  };

  const handleGroupSelect = () => {
    // Toggle selection: if already selected, deselect; otherwise select
    if (selectedGroupId === group.id) {
      onSelectGroup(null);
    } else {
      onSelectGroup(group);
    }
  };

  return (
    <>
      <div
        onClick={handleGroupSelect}
        style={{
          cursor: 'pointer',
          padding: '8px 12px',
          borderRadius: '4px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '4px',
        }}
      >
        <FolderIcon />
        <span style={{ flex: 1 }}>{group.name}</span>
        <div
          onClick={(e) => {
            e.stopPropagation();
            handleGroupChange();
          }}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '20px',
            height: '20px',
            borderRadius: '3px',
            cursor: 'pointer',
            // No background styling on expand/collapse
            fontSize: '12px',
            flexShrink: 0,
            // No transition
          }}
          title={isExpanded ? 'Collapse' : 'Expand'}
        >
          {/* Chevron icon */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            {isExpanded ? (
              // Chevron down
              <path d="M6 9l6 6 6-6" />
            ) : (
              // Chevron right
              <path d="M9 6l6 6-6 6" />
            )}
          </svg>
        </div>
      </div>
      <NavLink
        label=""
        leftSection={null}
        childrenOffset={0}
        opened={isExpanded}
        onChange={handleGroupChange}
        active={false}
        variant="subtle"
        style={{ display: 'none' }}
      ></NavLink>
      {isExpanded && (
        <Box pl="md">
          <MarketGroupTree
            groupChildrenMap={groupChildrenMap}
            parentId={group.id}
            onSelectType={onSelectType}
            onSelectGroup={onSelectGroup}
            selectedTypeId={selectedTypeId}
            selectedGroupId={selectedGroupId}
            expandedGroups={expandedGroups}
            toggleGroup={toggleGroup}
            filteredGroupIds={filteredGroupIds}
            injectedItems={injectedItems}
            isFiltering={isFiltering}
          />

          {/* Render types if this group has them */}
          {loadingTypes && <Loader size="xs" ml="md" />}
          {sortedItems.map((type) => (
            <NavLink
              key={type.id}
              label={type.name}
              leftSection={
                <EveIcon id={type.id} name={type.name} size={24} useAvatar radius="xs" />
              }
              active={selectedTypeId === type.id}
              onClick={(e) => {
                e.stopPropagation();
                onSelectType(type);
              }}
              pl="md"
              variant="light"
              component="button"
              style={{ textAlign: 'left' }}
            />
          ))}
        </Box>
      )}
    </>
  );
}

function ItemFilterWidget({
  onSelect,
  selectedItem,
  onSelectGroup,
  selectedGroup,
  searchValue,
  onSearchChange,
  resetTrigger,
}) {
  const [debouncedSearch] = useDebouncedValue(searchValue, 300);
  const [searchLoading, setSearchLoading] = useState(false);

  const [groups, setGroups] = useState([]);
  const [groupsLoading, setGroupsLoading] = useState(true);
  const [expandedGroups, setExpandedGroups] = useState(new Set());

  // Filter state
  const [filteredGroupIds, setFilteredGroupIds] = useState(new Set());
  const [injectedItems, setInjectedItems] = useState(new Map());
  const isFiltering = debouncedSearch.length >= 3;

  // Collapse all groups when resetTrigger changes
  useEffect(() => {
    if (resetTrigger > 0) {
      setExpandedGroups(new Set());
    }
  }, [resetTrigger]);

  // Fetch full group tree on mount
  useEffect(() => {
    const CACHE_KEY = 'lenny_market_groups_tree';
    const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours

    const fetchAndCache = () => {
      axios
        .get('http://localhost:8000/api/market/groups/tree')
        .then((res) => {
          setGroups(res.data);
          setGroupsLoading(false);
          try {
            localStorage.setItem(
              CACHE_KEY,
              JSON.stringify({
                timestamp: Date.now(),
                data: res.data,
              })
            );
          } catch (e) {
            console.error('Failed to cache market groups', e);
          }
        })
        .catch((err) => {
          console.error(err);
          setGroupsLoading(false);
        });
    };

    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (cached) {
        const { timestamp, data } = JSON.parse(cached);
        if (Date.now() - timestamp < CACHE_DURATION) {
          setGroups(data);
          setGroupsLoading(false);
          return;
        }
      }
    } catch (e) {
      console.warn('Invalid cache data', e);
    }

    fetchAndCache();
  }, []);

  const groupChildrenMap = useMemo(() => {
    const map = new Map();
    groups.forEach((g) => {
      const pid = g.parent_id || null;
      if (!map.has(pid)) map.set(pid, []);
      map.get(pid).push(g);
    });
    // Sort groups alphabetically
    map.forEach((children) => {
      children.sort((a, b) => a.name.localeCompare(b.name));
    });
    return map;
  }, [groups]);

  const groupMap = useMemo(() => {
    const map = new Map();
    groups.forEach((g) => map.set(g.id, g));
    return map;
  }, [groups]);

  // Handle search and filtering
  useEffect(() => {
    if (isFiltering) {
      setSearchLoading(true);

      // 1. Search items server-side
      axios
        .get(`http://localhost:8000/api/market/types/search?q=${debouncedSearch}&size=250`)
        .then((res) => {
          const foundItems = res.data.items;

          // 2. Calculate visible groups and injected items
          const visible = new Set();
          const injected = new Map();
          const autoExpanded = new Set();

          // Process found items
          foundItems.forEach((item) => {
            if (item.market_group_id) {
              // Add item to injected map
              if (!injected.has(item.market_group_id)) {
                injected.set(item.market_group_id, []);
              }
              injected.get(item.market_group_id).push(item);

              // Add group and ancestors to visible
              let currentId = item.market_group_id;
              while (currentId) {
                visible.add(currentId);
                autoExpanded.add(currentId);
                const group = groupMap.get(currentId);
                currentId = group ? group.parent_id : null;
              }
            }
          });

          // 3. Also filter groups by name (client-side)
          groups.forEach((group) => {
            if (group.name.toLowerCase().includes(debouncedSearch.toLowerCase())) {
              let currentId = group.id;
              while (currentId) {
                visible.add(currentId);
                // Only auto-expand parents, not the group itself (unless it has matches inside)
                const g = groupMap.get(currentId);
                if (g && g.parent_id) autoExpanded.add(g.parent_id);
                currentId = g ? g.parent_id : null;
              }
            }
          });

          setFilteredGroupIds(visible);
          setInjectedItems(injected);
          setExpandedGroups(autoExpanded);
          setSearchLoading(false);
        })
        .catch((err) => {
          console.error(err);
          setSearchLoading(false);
        });
    } else {
      // When not filtering, clear only the search-specific filters, but keep expanded groups and selected item
      setFilteredGroupIds(new Set());
      setInjectedItems(new Map());
      // Don't reset expandedGroups here - keep manually expanded groups open
      // Only deselect if we have a selected item (this will be called from parent)
    }
  }, [debouncedSearch, isFiltering, groups, groupMap]);

  const toggleGroup = (groupId) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(groupId)) {
      newExpanded.delete(groupId);
    } else {
      newExpanded.add(groupId);
    }
    setExpandedGroups(newExpanded);
  };

  const clearSearch = () => {
    onSearchChange('');
    // Don't close expanded groups or deselect items when clearing search
  };

  const handleSelectType = (type) => {
    // Only allow one item selection at a time - clear group selection
    onSelectGroup(null);
    onSelect(type);
  };

  const handleSelectGroup = (group) => {
    // When selecting a group, clear item selection
    onSelectGroup(group);
    onSelect(null);
  };

  const removeSelectedItem = () => {
    onSelect(null);
    onSearchChange('');
  };

  const removeSelectedGroup = () => {
    onSelectGroup(null);
  };

  return (
    <Paper
      shadow="xs"
      p="md"
      withBorder
      display="flex"
      style={{ flexDirection: 'column', height: '100%', minHeight: 0 }}
    >
      <Title order={4} mb="sm" size="h5">
        Item Browser ({groups.length})
      </Title>

      {/* Selected Filters Section */}
      {(selectedItem || selectedGroup) && (
        <Stack mb="sm" gap="xs">
          <Text size="xs" fw={600} c="dimmed">
            Selected Filter:
          </Text>
          {selectedItem && (
            <Badge
              size="lg"
              variant="light"
              color="blue"
              leftSection={<EveIcon id={selectedItem.id} name={selectedItem.name} size={20} />}
              rightSection={
                <CloseButton
                  size="xs"
                  onClick={removeSelectedItem}
                  aria-label="Remove item filter"
                />
              }
              style={{ paddingRight: '4px', cursor: 'default' }}
            >
              {selectedItem.name}
            </Badge>
          )}
          {selectedGroup && (
            <Badge
              size="lg"
              variant="light"
              color="grape"
              leftSection={<FolderIcon />}
              rightSection={
                <CloseButton
                  size="xs"
                  onClick={removeSelectedGroup}
                  aria-label="Remove group filter"
                />
              }
              style={{ paddingRight: '4px', cursor: 'default' }}
            >
              {selectedGroup.name}
            </Badge>
          )}
        </Stack>
      )}

      <Stack mb="sm" gap="xs">
        <TextInput
          placeholder="Search item..."
          value={searchValue}
          onChange={(e) => onSearchChange(e.currentTarget.value)}
          size="sm"
          rightSection={
            searchLoading ? (
              <Loader size="xs" />
            ) : searchValue ? (
              <CloseButton
                aria-label="Clear search"
                onClick={() => clearSearch()}
                style={{ display: 'block' }}
              />
            ) : null
          }
        />
      </Stack>

      <Text size="xs" fw={500} mb="xs">
        Market Groups
      </Text>
      <ScrollArea style={{ flex: 1, minHeight: 0 }} type="auto" scrollbarSize={6}>
        {groupsLoading ? (
          <Loader size="sm" />
        ) : groups.length > 0 ? (
          <MarketGroupTree
            groupChildrenMap={groupChildrenMap}
            parentId={null}
            onSelectType={handleSelectType}
            onSelectGroup={handleSelectGroup}
            selectedTypeId={selectedItem?.id}
            selectedGroupId={selectedGroup?.id}
            expandedGroups={expandedGroups}
            toggleGroup={toggleGroup}
            filteredGroupIds={filteredGroupIds}
            injectedItems={injectedItems}
            isFiltering={isFiltering}
          />
        ) : (
          <Text size="sm" c="dimmed" ta="center" mt="md">
            No market groups found
          </Text>
        )}
      </ScrollArea>
    </Paper>
  );
}

export default ItemFilterWidget;
