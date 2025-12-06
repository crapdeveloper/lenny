import React, { useState, useEffect } from 'react';
import { Image, Avatar, Skeleton } from '@mantine/core';

/**
 * Generates the URL for EVE Online images from the official image CDN.
 * @param {number} id - The type ID, character ID, corporation ID, or alliance ID
 * @param {string} name - The name of the item (used for blueprint detection)
 * @param {string} type - The type of entity: 'type', 'character', 'corporation', or 'alliance'
 * @param {string} variant - The variant of the image:
 *   - 'icon': Default item icon (small, square)
 *   - 'render': 3D rendered image of ships/items
 *   - 'bp': Blueprint icon
 * @returns {string} The base URL for the image (without size parameter)
 */
export const getEveIconUrl = (id, name, type = 'type', variant = 'icon') => {
  if (type === 'character') return `https://images.evetech.net/characters/${id}/portrait`;
  if (type === 'corporation') return `https://images.evetech.net/corporations/${id}/logo`;
  if (type === 'alliance') return `https://images.evetech.net/alliances/${id}/logo`;

  // Inventory types
  if (name && (name.includes('Blueprint') || name.includes('Formula'))) {
    return `https://images.evetech.net/types/${id}/bp`;
  }
  return `https://images.evetech.net/types/${id}/${variant}`;
};

const EveIcon = ({
  id,
  name,
  type = 'type',
  variant = 'icon',
  size = 32,
  useAvatar = false,
  maxRetries = 3,
  ...props
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [showSkeleton, setShowSkeleton] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  // Delay skeleton visibility to avoid flash on cached images
  useEffect(() => {
    const timer = setTimeout(() => {
      if (loading) {
        setShowSkeleton(true);
      }
    }, 100);

    return () => clearTimeout(timer);
  }, [loading]);

  // EVE Image server supports sizes: 32, 64, 128, 256, 512, 1024 (for some)
  // We'll pick a size that ensures quality.
  const targetSize = size <= 32 ? 64 : size <= 64 ? 64 : 128;

  // Add cache-busting parameter only on retries to bypass browser cache when retrying
  const url = `${getEveIconUrl(id, name, type, variant)}?size=${targetSize}${
    retryCount > 0 ? `&retry=${retryCount}&t=${Date.now()}` : ''
  }`;

  const handleLoad = () => {
    setLoading(false);
  };

  const handleError = () => {
    setLoading(false);

    // Log errors in development only
    if (import.meta.env.DEV) {
      console.error('Failed to load EVE icon:', {
        id,
        type,
        variant,
        url,
        retryCount: retryCount + 1,
        maxRetries,
      });
    }

    // Retry if we haven't exceeded max retries
    if (retryCount < maxRetries) {
      // Exponential backoff: 500ms, 1s, 2s
      const delay = Math.min(500 * Math.pow(2, retryCount), 2000);
      const timer = setTimeout(() => {
        setRetryCount(retryCount + 1);
      }, delay);
      return () => clearTimeout(timer);
    } else {
      // Max retries exceeded, show error state
      setError(true);
    }
  };

  // Color palette for fallback avatars
  const colors = [
    'blue',
    'red',
    'green',
    'yellow',
    'orange',
    'purple',
    'teal',
    'cyan',
    'pink',
    'grape',
  ];
  const fallbackColor = colors[id % 10];

  // Show fallback on error
  if (error) {
    return (
      <Avatar color={fallbackColor} size={size} {...props}>
        ?
      </Avatar>
    );
  }

  if (useAvatar) {
    return (
      <>
        {showSkeleton && loading && (
          <Skeleton height={size} width={size} circle={true} {...props} />
        )}
        <Avatar
          src={url}
          size={size}
          onLoad={handleLoad}
          onError={handleError}
          style={{ display: loading ? 'none' : 'block' }}
          {...props}
        />
      </>
    );
  }

  return (
    <>
      {showSkeleton && loading && <Skeleton height={size} width={size} {...props} />}
      <Image
        src={url}
        w={size}
        h={size}
        fit="contain"
        onLoad={handleLoad}
        onError={handleError}
        style={{ display: loading ? 'none' : 'block' }}
        {...props}
      />
    </>
  );
};

export default EveIcon;
