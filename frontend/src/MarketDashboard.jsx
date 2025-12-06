import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import axios from 'axios';
import {
  Table,
  Title,
  Loader,
  Badge,
  Paper,
  TextInput,
  Select,
  Group,
  Stack,
  Image,
  Text,
  HoverCard,
  Button,
  Collapse,
  Center,
  ScrollArea,
  Box,
} from '@mantine/core';
import { useVirtualizer } from '@tanstack/react-virtual';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official';
import 'highcharts/highcharts-more';
import EveIcon from './EveIcon';

const ItemHoverCard = React.memo(function ItemHoverCard({ typeId, typeName, children }) {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchDetails = useCallback(() => {
    if (details) return;
    setLoading(true);
    axios
      .get(`http://localhost:8000/api/market/types/${typeId}/details`)
      .then((res) => {
        setDetails(res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, [details, typeId]);

  return (
    <HoverCard width={320} shadow="md" onOpen={fetchDetails}>
      <HoverCard.Target>{children}</HoverCard.Target>
      <HoverCard.Dropdown>
        <Text size="sm" fw={500} mb="xs">
          {typeName}
        </Text>
        {loading ? (
          <Loader size="sm" />
        ) : details ? (
          <Stack gap="xs">
            <Text size="xs" dangerouslySetInnerHTML={{ __html: details.description }} />
            <Group gap="xs">
              <Badge size="xs" variant="outline">
                Volume: {details.volume} m3
              </Badge>
              {details.mass && (
                <Badge size="xs" variant="outline">
                  Mass: {details.mass} kg
                </Badge>
              )}
            </Group>
          </Stack>
        ) : (
          <Text size="xs" c="dimmed">
            No details available
          </Text>
        )}
      </HoverCard.Dropdown>
    </HoverCard>
  );
});

const MarketHistoryChart = React.memo(function MarketHistoryChart({
  regionId,
  typeId,
  colorScheme = 'light',
}) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    axios
      .get(`http://localhost:8000/api/market/history`, {
        params: { region_id: regionId, type_id: typeId },
      })
      .then((res) => {
        setHistory(res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, [regionId, typeId]);

  if (loading) return <Loader size="sm" />;
  if (!history.length)
    return (
      <Text size="sm" c="dimmed">
        No history available
      </Text>
    );

  // Apply HighCharts theme based on color scheme
  if (colorScheme === 'dark') {
    Highcharts.setOptions({
      colors: [
        '#1f77b4',
        '#ff7f0e',
        '#2ca02c',
        '#d62728',
        '#9467bd',
        '#8c564b',
        '#e377c2',
        '#7f7f7f',
        '#bcbd22',
        '#17becf',
      ],
      chart: { backgroundColor: '#1a1a1a', borderColor: '#333333' },
      title: { style: { color: '#e0e0e0' } },
      subtitle: { style: { color: '#b0b0b0' } },
      legend: { backgroundColor: 'transparent', itemStyle: { color: '#e0e0e0' } },
      xAxis: {
        labels: { style: { color: '#b0b0b0' } },
        title: { style: { color: '#e0e0e0' } },
        lineColor: '#333333',
        tickColor: '#333333',
      },
      yAxis: {
        labels: { style: { color: '#b0b0b0' } },
        title: { style: { color: '#e0e0e0' } },
        lineColor: '#333333',
        tickColor: '#333333',
        gridLineColor: '#2a2a2a',
      },
      plotOptions: { series: { dataLabels: { color: '#e0e0e0' }, shadow: false } },
      tooltip: { backgroundColor: '#2a2a2a', borderColor: '#555555', style: { color: '#e0e0e0' } },
      credits: { style: { color: '#b0b0b0' } },
    });
  } else {
    Highcharts.setOptions({
      colors: [
        '#1f77b4',
        '#ff7f0e',
        '#2ca02c',
        '#d62728',
        '#9467bd',
        '#8c564b',
        '#e377c2',
        '#7f7f7f',
        '#bcbd22',
        '#17becf',
      ],
      chart: { backgroundColor: '#ffffff', borderColor: '#e0e0e0' },
      title: { style: { color: '#000000' } },
      subtitle: { style: { color: '#666666' } },
      legend: { backgroundColor: 'transparent', itemStyle: { color: '#333333' } },
      xAxis: {
        labels: { style: { color: '#666666' } },
        title: { style: { color: '#000000' } },
        lineColor: '#e0e0e0',
        tickColor: '#e0e0e0',
      },
      yAxis: {
        labels: { style: { color: '#666666' } },
        title: { style: { color: '#000000' } },
        lineColor: '#e0e0e0',
        tickColor: '#e0e0e0',
        gridLineColor: '#f0f0f0',
      },
      plotOptions: { series: { dataLabels: { color: '#000000' }, shadow: false } },
      tooltip: { backgroundColor: '#f9f9f9', borderColor: '#cccccc', style: { color: '#000000' } },
      credits: { style: { color: '#999999' } },
    });
  }

  const options = {
    title: { text: 'Market History' },
    xAxis: {
      type: 'datetime',
      title: { text: 'Date' },
      min: (function () {
        try {
          const rangeMs = 90 * 24 * 60 * 60 * 1000; // 90 days
          if (!history || !history.length) return undefined;
          const times = history.map((h) => new Date(h.date).getTime()).filter((t) => !!t);
          if (!times.length) return undefined;
          const last = times[times.length - 1];
          const first = times[0];
          return Math.max(first, last - rangeMs);
        } catch (e) {
          return undefined;
        }
      })(),
    },
    yAxis: [
      {
        title: { text: 'Price (ISK)' },
        lineWidth: 2,
        labels: {
          format: '{value} ISK',
        },
      },
      {
        title: { text: 'Volume' },
        opposite: true,
        lineWidth: 2,
        labels: {
          format: '{value}',
        },
      },
      {
        title: { text: 'Daily Range' },
        opposite: true,
        lineWidth: 2,
        labels: {
          format: '{value} ISK',
        },
      },
    ],
    series: (function () {
      // Prepare base arrays
      const times = history.map((h) => new Date(h.date).getTime());
      const prices = history.map((h) => h.average);

      // Simple moving average helper
      const sma = (data, window) => {
        const out = Array(data.length).fill(null);
        let sum = 0;
        for (let i = 0; i < data.length; i++) {
          sum += data[i];
          if (i >= window) {
            sum -= data[i - window];
          }
          if (i >= window - 1) {
            out[i] = sum / window;
          }
        }
        return out;
      };

      // Rolling standard deviation for a window aligned with sma
      const rollingStd = (data, window) => {
        const out = Array(data.length).fill(null);
        for (let i = 0; i < data.length; i++) {
          if (i >= window - 1) {
            let sum = 0;
            let mean = 0;
            for (let j = i - (window - 1); j <= i; j++) {
              sum += data[j];
            }
            mean = sum / window;
            let sq = 0;
            for (let j = i - (window - 1); j <= i; j++) {
              const d = data[j] - mean;
              sq += d * d;
            }
            out[i] = Math.sqrt(sq / window);
          }
        }
        return out;
      };

      const ma7 = sma(prices, 7);
      const ma30 = sma(prices, 30);
      const sd30 = rollingStd(prices, 30);
      const bandMultiplier = 2;

      // Build series data
      const priceRangeSeries = history.map((h) => [
        new Date(h.date).getTime(),
        h.lowest,
        h.highest,
      ]);
      const avgSeries = history.map((h) => [new Date(h.date).getTime(), h.average]);
      const volumeSeries = history.map((h) => [new Date(h.date).getTime(), h.volume]);
      const dailyRangeSeries = history.map((h) => [
        new Date(h.date).getTime(),
        h.highest - h.lowest,
      ]);

      const ma7Series = ma7.map((v, i) => (v == null ? null : [times[i], parseFloat(v)]));
      const ma30Series = ma30.map((v, i) => (v == null ? null : [times[i], parseFloat(v)]));

      const volBandSeries = sd30.map((sd, i) => {
        if (sd == null || ma30[i] == null) return null;
        const upper = ma30[i] + bandMultiplier * sd;
        const lower = ma30[i] - bandMultiplier * sd;
        return [times[i], lower, upper];
      });

      // Filter out nulls for line series (Highcharts tolerates nulls in arrays, but keep consistent)
      const ma7Data = ma7Series;
      const ma30Data = ma30Series;
      const volBandData = volBandSeries;

      return [
        {
          type: 'arearange',
          name: 'Price Range',
          data: priceRangeSeries,
          yAxis: 0,
          color: Highcharts.getOptions().colors[0],
          fillOpacity: 0.2,
          zIndex: 0,
          marker: { enabled: false },
        },
        {
          type: 'arearange',
          name: 'Volatility Band (MA30 ± 2σ)',
          data: volBandData,
          yAxis: 0,
          color: Highcharts.getOptions().colors[2],
          fillOpacity: 0.08,
          zIndex: 0.5,
          marker: { enabled: false },
          linkedTo: undefined,
        },
        {
          type: 'line',
          name: 'MA (30)',
          data: ma30Data,
          yAxis: 0,
          color: Highcharts.getOptions().colors[2],
          zIndex: 2,
          marker: { enabled: false },
        },
        {
          type: 'line',
          name: 'MA (7)',
          data: ma7Data,
          yAxis: 0,
          color: Highcharts.getOptions().colors[1],
          zIndex: 3,
          marker: { enabled: false },
        },
        {
          type: 'line',
          name: 'Average Price',
          data: avgSeries,
          yAxis: 0,
          zIndex: 4,
          marker: { enabled: true, radius: 2 },
        },
        {
          type: 'column',
          name: 'Volume',
          data: volumeSeries,
          yAxis: 1,
          opacity: 0.4,
          zIndex: 0,
        },
        {
          type: 'line',
          name: 'Daily Range (High - Low)',
          data: dailyRangeSeries,
          yAxis: 2,
          color: '#f7a35c',
          zIndex: 2,
          marker: { enabled: true, radius: 2 },
        },
      ];
    })(),
    chart: {
      height: 400,
      zoomType: 'x',
    },
    plotOptions: {
      area: {
        marker: {
          radius: 2,
        },
        lineWidth: 1,
        states: {
          hover: {
            lineWidth: 1,
          },
        },
        threshold: null,
      },
    },
  };

  return <HighchartsReact key={colorScheme} highcharts={Highcharts} options={options} />;
});

function MarketDashboard({
  selectedItem,
  selectedGroup,
  selectedLocation,
  orderType,
  colorScheme = 'light',
  onItemSearchIconClick,
  onLocationSearchIconClick,
}) {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [expandedRow, setExpandedRow] = useState(null);
  const parentRef = useRef(null);
  const loadingRef = useRef(false);
  const hasMoreRef = useRef(true);
  const seenIdsRef = useRef(new Set());
  const inFlightPagesRef = useRef(new Set());

  const fetchOrders = useCallback(
    (pageNum = 1, append = false) => {
      // Always set loading when fetching
      setLoading(true);
      loadingRef.current = true;

      const MAX_ROWS = 5000;
      const params = {
        page: pageNum,
        size: 25,
      };

      if (selectedItem) {
        params.type_id = selectedItem.id;
      }
      if (selectedGroup) {
        params.market_group_id = selectedGroup.id;
      }
      if (orderType !== 'all') {
        params.is_buy_order = orderType === 'buy';
      }

      // Add location filter based on selected location type
      if (selectedLocation?.type === 'station') {
        params.station_id = selectedLocation.id;
      } else if (selectedLocation?.type === 'system') {
        params.solar_system_id = selectedLocation.id;
      } else if (selectedLocation?.type === 'region') {
        params.region_id = selectedLocation.id;
      }
      // If selectedLocation is null, no location param is sent (all regions)

      console.log('Fetching orders:', { pageNum, append, params, selectedGroup, selectedItem });
      // Prevent parallel fetches for the same page
      if (inFlightPagesRef.current.has(pageNum)) {
        console.debug('Fetch already in-flight for page', pageNum);
        setLoading(false);
        loadingRef.current = false;
        return;
      }
      inFlightPagesRef.current.add(pageNum);

      axios
        .get('http://localhost:8000/api/market/orders', { params })
        .then((res) => {
          console.log('Received orders:', {
            pageNum,
            itemsCount: res.data.items.length,
            totalPages: res.data.pages,
          });
          const incoming = res.data.items || [];

          if (append) {
            // Fast dedupe using seenIdsRef (only O(pageSize) work)
            const uniqueToAdd = [];
            const dupIds = [];
            for (const item of incoming) {
              if (!seenIdsRef.current.has(item.order_id)) {
                seenIdsRef.current.add(item.order_id);
                uniqueToAdd.push(item);
              } else {
                dupIds.push(item.order_id);
              }
            }
            if (dupIds.length) {
              console.warn('Duplicate order_ids received while appending', {
                page: pageNum,
                duplicateCount: dupIds.length,
                sampleDuplicates: dupIds.slice(0, 10),
              });
            }

            setOrders((prev) => {
              const merged = prev.concat(uniqueToAdd);
              return merged.slice(0, MAX_ROWS);
            });
          } else {
            // Replace entire list and rebuild seen set
            seenIdsRef.current = new Set(incoming.map((i) => i.order_id));
            setOrders(incoming.slice(0, MAX_ROWS));
          }

          // Check if there are more pages
          const hasMorePages =
            pageNum < res.data.pages &&
            (append ? orders.length < MAX_ROWS : res.data.items.length > 0);
          setHasMore(hasMorePages);
          hasMoreRef.current = hasMorePages;
          setLoading(false);
          loadingRef.current = false;
        })
        .catch((err) => {
          console.error('Error fetching orders:', err);
          setLoading(false);
          loadingRef.current = false;
          setHasMore(false);
          hasMoreRef.current = false;
        })
        .finally(() => {
          inFlightPagesRef.current.delete(pageNum);
        });
    },
    [selectedLocation, orderType, selectedItem, selectedGroup]
  );

  // Initial fetch and reset on filter changes
  useEffect(() => {
    setPage(1);
    setHasMore(true);
    hasMoreRef.current = true;
    loadingRef.current = false;
    fetchOrders(1, false);
  }, [selectedItem, selectedGroup, selectedLocation, orderType]);

  // Store fetchOrders in a ref to avoid recreating observer
  const fetchOrdersRef = useRef(fetchOrders);
  fetchOrdersRef.current = fetchOrders;

  const handleLocationClick = useCallback(
    (location) => {
      if (onLocationSearchIconClick) onLocationSearchIconClick(location);
    },
    [onLocationSearchIconClick]
  );

  const handleStationClick = useCallback(
    (order) => {
      // If we already have station_id, use it
      if (order.station_id) {
        handleLocationClick({ type: 'station', id: order.station_id, name: order.station_name });
        return;
      }

      // Fallback: try to resolve station by name via search endpoint
      const q = order.station_name || '';
      if (!q) return;
      axios
        .get('http://localhost:8000/api/market/locations/search', { params: { q } })
        .then((res) => {
          const results = res.data || [];
          // Prefer exact station match
          let match = results.find((r) => r.type === 'station' && r.name === order.station_name);
          if (!match) match = results.find((r) => r.type === 'station');
          if (match) {
            handleLocationClick(match);
          } else {
            console.warn('No station match found for', order.station_name);
          }
        })
        .catch((err) => {
          console.error('Error resolving station by name:', err);
        });
    },
    [handleLocationClick]
  );

  const formatTimeRemaining = (issued, duration) => {
    const issuedDate = new Date(issued);
    const expiryDate = new Date(issuedDate.getTime() + duration * 24 * 60 * 60 * 1000);
    const now = new Date();
    const diff = expiryDate - now;

    if (diff <= 0) return 'Expired';

    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));

    if (days > 0) return `${days}d ${hours}h`;
    return `${hours}h`;
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const toggleRow = useCallback((orderId) => {
    setExpandedRow((prev) => (prev === orderId ? null : orderId));
  }, []);

  // Virtual scrolling setup - must be defined before useEffect that uses it
  const rowVirtualizer = useVirtualizer({
    count: orders.length,
    getScrollElement: () => parentRef.current,
    estimateSize: useCallback(
      (index) => {
        // Base row height + expanded chart height if this row is expanded
        const order = orders[index];
        return expandedRow === order?.order_id ? 500 : 80;
      },
      [orders, expandedRow]
    ),
    overscan: 10,
    measureElement:
      typeof window !== 'undefined' && navigator.userAgent.indexOf('Firefox') === -1
        ? (element) => element?.getBoundingClientRect().height
        : undefined,
  });

  // Infinite scroll with virtual scrolling
  useEffect(() => {
    const [lastItem] = [...rowVirtualizer.getVirtualItems()].reverse();

    if (!lastItem) return;

    // Load more when user scrolls near the end
    if (
      lastItem.index >= orders.length - 5 &&
      hasMoreRef.current &&
      orders.length < 5000 &&
      !loadingRef.current
    ) {
      console.log('Loading next page from virtual scroll:', page + 1);
      const nextPage = page + 1;
      setPage(nextPage);
      fetchOrdersRef.current(nextPage, true);
    }
  }, [rowVirtualizer.getVirtualItems(), orders.length, page]);

  return (
    <Paper shadow="xs" p="md" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Title order={2} mb="md">
        Market Dashboard
      </Title>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        {loading && page === 1 ? (
          <Center mt="xl">
            <Loader />
          </Center>
        ) : orders.length === 0 ? (
          <Center mt="xl">
            <Text size="sm" c="dimmed">
              No orders found
            </Text>
          </Center>
        ) : (
          <>
            <Box ref={parentRef} style={{ flex: 1, overflow: 'auto' }}>
              {/* Header rendered as CSS grid to match body column layout */}
              <div
                style={{
                  position: 'sticky',
                  top: 0,
                  zIndex: 10,
                  backgroundColor: 'var(--mantine-color-body)',
                }}
              >
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '20% 10% 8% 12% 10% 20% 12% 8%',
                    gap: 0,
                    padding: '8px 12px',
                    fontWeight: 600,
                  }}
                >
                  <div>Item</div>
                  <div>Region</div>
                  <div>Type</div>
                  <div>Price</div>
                  <div>Volume</div>
                  <div>Station</div>
                  <div>Created</div>
                  <div>Expires In</div>
                </div>
              </div>
              <div
                style={{
                  height: `${rowVirtualizer.getTotalSize()}px`,
                  position: 'relative',
                  width: '100%',
                }}
              >
                {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                  const order = orders[virtualRow.index];
                  const isExpanded = expandedRow === order.order_id;
                  const rowBg =
                    virtualRow.index % 2 === 0 ? 'transparent' : 'rgba(255, 255, 255, 0.04)';

                  return (
                    <div
                      key={order.order_id}
                      data-index={virtualRow.index}
                      ref={rowVirtualizer.measureElement}
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        // Let content determine height; virtualizer measures it
                        transform: `translateY(${virtualRow.start}px)`,
                      }}
                    >
                      <div
                        role="row"
                        style={{
                          display: 'grid',
                          gridTemplateColumns: '20% 10% 8% 12% 10% 20% 12% 8%',
                          gap: 0,
                          padding: '8px 12px',
                          alignItems: 'center',
                          background: rowBg,
                          cursor: 'pointer',
                        }}
                        onClick={() => toggleRow(order.order_id)}
                      >
                        <div
                          style={{ display: 'flex', gap: 8, alignItems: 'flex-start', minWidth: 0 }}
                        >
                          <ItemHoverCard typeId={order.type_id} typeName={order.type_name}>
                            <Group
                              gap="xs"
                              style={{ alignItems: 'flex-start', flex: 1, minWidth: 0 }}
                            >
                              <EveIcon id={order.type_id} name={order.type_name} size={32} />
                              <div
                                style={{
                                  display: 'inline-flex',
                                  gap: 6,
                                  alignItems: 'center',
                                  flexWrap: 'wrap',
                                  minWidth: 0,
                                }}
                              >
                                <Text
                                  size="sm"
                                  style={{
                                    wordBreak: 'break-word',
                                    minWidth: 0,
                                    cursor: 'pointer',
                                    textDecoration: 'underline dotted',
                                    textDecorationColor: 'rgba(128,128,128,0.6)',
                                  }}
                                  tabIndex={0}
                                  role="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    if (onItemSearchIconClick)
                                      onItemSearchIconClick({
                                        id: order.type_id,
                                        name: order.type_name,
                                      });
                                  }}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter' || e.key === ' ') {
                                      e.preventDefault();
                                      e.stopPropagation();
                                      if (onItemSearchIconClick)
                                        onItemSearchIconClick({
                                          id: order.type_id,
                                          name: order.type_name,
                                        });
                                    }
                                  }}
                                >
                                  {order.type_name}
                                </Text>
                              </div>
                            </Group>
                          </ItemHoverCard>
                        </div>

                        <div
                          style={{
                            display: 'inline-flex',
                            gap: 6,
                            alignItems: 'center',
                            flexWrap: 'wrap',
                            minWidth: 0,
                          }}
                        >
                          <Text
                            size="sm"
                            style={{
                              minWidth: 0,
                              cursor: 'pointer',
                              textDecoration: 'underline dotted',
                              textDecorationColor: 'rgba(128,128,128,0.6)',
                            }}
                            tabIndex={0}
                            role="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              if (onLocationSearchIconClick)
                                onLocationSearchIconClick({
                                  type: 'region',
                                  id: order.region_id,
                                  name: order.region_name,
                                });
                            }}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' || e.key === ' ') {
                                e.preventDefault();
                                e.stopPropagation();
                                if (onLocationSearchIconClick)
                                  onLocationSearchIconClick({
                                    type: 'region',
                                    id: order.region_id,
                                    name: order.region_name,
                                  });
                              }
                            }}
                          >
                            {order.region_name}
                          </Text>
                        </div>

                        <div
                          style={{
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {order.is_buy_order ? (
                            <Badge color="green">Buy</Badge>
                          ) : (
                            <Badge color="red">Sell</Badge>
                          )}
                        </div>

                        <div
                          style={{
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {order.price.toLocaleString()} ISK
                        </div>
                        <div
                          style={{
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {order.volume_remain.toLocaleString()}
                        </div>

                        <div
                          style={{
                            display: 'inline-flex',
                            gap: 6,
                            alignItems: 'center',
                            flexWrap: 'wrap',
                            minWidth: 0,
                          }}
                        >
                          <Text
                            size="sm"
                            style={{
                              minWidth: 0,
                              cursor: 'pointer',
                              textDecoration: 'underline dotted',
                              textDecorationColor: 'rgba(128,128,128,0.6)',
                            }}
                            tabIndex={0}
                            role="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleStationClick(order);
                            }}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' || e.key === ' ') {
                                e.preventDefault();
                                e.stopPropagation();
                                handleStationClick(order);
                              }
                            }}
                          >
                            {order.station_name}
                          </Text>
                        </div>

                        <div
                          style={{
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {formatDate(order.issued)}
                        </div>
                        <div
                          style={{
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {formatTimeRemaining(order.issued, order.duration)}
                        </div>
                      </div>

                      {isExpanded && (
                        <div style={{ background: rowBg }}>
                          <div style={{ gridColumn: '1 / -1', padding: 8 }}>
                            <Paper p={8} withBorder style={{ margin: 0 }}>
                              <MarketHistoryChart
                                regionId={order.region_id}
                                typeId={order.type_id}
                                colorScheme={colorScheme}
                              />
                            </Paper>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Loading indicator for next page */}
              {loading && page > 1 && (
                <Center mt="md" mb="md">
                  <Stack align="center" gap="sm">
                    <Loader size="md" />
                    <Text size="sm" c="dimmed">
                      Loading more orders...
                    </Text>
                  </Stack>
                </Center>
              )}

              {/* End of data message */}
              {!hasMore && (
                <Center mt="md" mb="md">
                  <Paper
                    p="md"
                    withBorder
                    radius="md"
                    bg="gray.0"
                    style={{ borderStyle: 'dashed' }}
                  >
                    <Text size="sm" c="dimmed" fw={500}>
                      End of data - No more orders to display
                    </Text>
                  </Paper>
                </Center>
              )}
            </Box>
          </>
        )}
      </div>
    </Paper>
  );
}

export default MarketDashboard;
