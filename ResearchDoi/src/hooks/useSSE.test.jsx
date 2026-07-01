/* global global */
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useSSE } from './useSSE';

// Mock EventSource
class MockEventSource {
  constructor(url) {
    this.url = url;
    MockEventSource.instances.push(this);
  }
  close = vi.fn();
}
MockEventSource.instances = [];

describe('useSSE', () => {
  beforeEach(() => {
    global.EventSource = MockEventSource;
    MockEventSource.instances = [];
    vi.clearAllMocks();
  });

  afterEach(() => {
    delete global.EventSource;
  });

  it('initializes with initialThesis', () => {
    const { result } = renderHook(() => useSSE('proj-123', { section_1: 'Hello' }));
    expect(result.current).toEqual({ section_1: 'Hello' });
  });

  it('connects to EventSource with the correct URL', () => {
    renderHook(() => useSSE('proj-123', {}));
    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toContain('/api/stream/proj-123');
  });

  it('applies JSON patch on message event', () => {
    const { result } = renderHook(() => useSSE('proj-123', { section_1: 'Hello' }));
    
    const eventSource = MockEventSource.instances[0];
    
    act(() => {
      // Simulate an SSE message with a JSON patch
      eventSource.onmessage({
        data: JSON.stringify({ op: 'replace', path: '/section_1', value: 'Hello World' })
      });
    });

    expect(result.current).toEqual({ section_1: 'Hello World' });
  });

  it('handles deep object patches', () => {
    const { result } = renderHook(() => useSSE('proj-123', { metadata: { status: 'draft' } }));
    
    const eventSource = MockEventSource.instances[0];
    
    act(() => {
      eventSource.onmessage({
        data: JSON.stringify({ op: 'replace', path: '/metadata/status', value: 'published' })
      });
    });

    expect(result.current.metadata.status).toBe('published');
  });

  it('closes EventSource on unmount', () => {
    const { unmount } = renderHook(() => useSSE('proj-123', {}));
    const eventSource = MockEventSource.instances[0];
    unmount();
    expect(eventSource.close).toHaveBeenCalledTimes(1);
  });
});
