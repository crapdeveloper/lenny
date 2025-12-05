import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Affix, ActionIcon, Card, ScrollArea, TextInput, Button, Stack, Group, Text, Loader, Transition, Table, Code, Divider, UnstyledButton, Modal } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const MarkdownComponents = {
  table: (props) => <Table highlightOnHover withTableBorder withColumnBorders bg="white" c="black" {...props} />,
  thead: (props) => <Table.Thead bg="gray.2" c="black" {...props} />,
  tbody: (props) => <Table.Tbody c="black" {...props} />,
  tr: (props) => <Table.Tr {...props} />,
  th: (props) => <Table.Th c="black" {...props} />,
  td: (props) => <Table.Td c="black" {...props} />,
  code: ({node, inline, className, children, ...props}) => {
    return inline ? (
      <Code c="black" bg="gray.2" {...props}>{children}</Code>
    ) : (
      <Code block c="black" bg="gray.0" {...props}>{children}</Code>
    );
  }
};

const ChatWidget = ({ characterId }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [view, setView] = useState('list'); // 'list' or 'chat'
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const [deleteId, setDeleteId] = useState(null);
  const [deleteModalOpened, { open: openDeleteModal, close: closeDeleteModal }] = useDisclosure(false);

  const [chatPosition, setChatPosition] = useState({ bottom: 20, right: 20 });
  const [resetKey, setResetKey] = useState(0);
  const isDragging = useRef(false);
  const dragOffset = useRef({ x: 0, y: 0 });

  const handleMouseMove = useCallback((e) => {
    if (!isDragging.current) return;
    setChatPosition({
      top: e.clientY - dragOffset.current.y,
      left: e.clientX - dragOffset.current.x
    });
  }, []);

  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
    document.body.style.userSelect = '';
  }, [handleMouseMove]);

  const handleMouseDown = (e) => {
    if (e.target.closest('button') || e.target.closest('.mantine-ActionIcon-root')) return;
    
    isDragging.current = true;
    const card = e.currentTarget.closest('.mantine-Card-root');
    const rect = card.getBoundingClientRect();
    
    dragOffset.current = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    };
    
    setChatPosition({
      top: rect.top,
      left: rect.left
    });

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.userSelect = 'none';
  };

  const handleResetPosition = () => {
    setChatPosition({ bottom: 20, right: 20 });
    setResetKey(prev => prev + 1);
  };

  const toggleChat = () => setIsOpen(!isOpen);

  useEffect(() => {
    if (isOpen && characterId && view === 'list') {
      fetchConversations();
    }
  }, [isOpen, characterId, view]);

  const fetchConversations = async () => {
    if (!characterId) return;
    try {
      const res = await fetch('http://localhost:8000/chat/conversations', {
        headers: { 'X-Character-Id': characterId }
      });
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const createConversation = async () => {
    if (!characterId) return;
    setIsLoading(true);
    try {
      const res = await fetch('http://localhost:8000/chat/conversations', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-Character-Id': characterId 
        },
        body: JSON.stringify({ title: 'New Chat' })
      });
      if (res.ok) {
        const data = await res.json();
        setCurrentConversationId(data.id);
        setMessages([]);
        setView('chat');
        fetchConversations();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const loadConversation = async (id) => {
    if (!characterId) return;
    setIsLoading(true);
    setCurrentConversationId(id);
    try {
      const res = await fetch(`http://localhost:8000/chat/conversations/${id}/messages`, {
        headers: { 'X-Character-Id': characterId }
      });
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
        setView('chat');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const confirmDelete = (e, id) => {
    e.stopPropagation();
    setDeleteId(id);
    openDeleteModal();
  };

  const handleDelete = async () => {
    if (!deleteId || !characterId) return;
    try {
      const res = await fetch(`http://localhost:8000/chat/conversations/${deleteId}`, {
        method: 'DELETE',
        headers: { 'X-Character-Id': characterId }
      });
      if (res.ok) {
        setConversations(prev => prev.filter(c => c.id !== deleteId));
        if (currentConversationId === deleteId) {
            setView('list');
            setCurrentConversationId(null);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      closeDeleteModal();
      setDeleteId(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || !characterId || !currentConversationId) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Character-Id': characterId
        },
        body: JSON.stringify({
          conversation_id: currentConversationId,
          message: input
        }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.content }]);
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I encountered an error." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <Modal opened={deleteModalOpened} onClose={closeDeleteModal} title="Delete Conversation" centered>
        <Text>Are you sure you want to delete this conversation?</Text>
        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={closeDeleteModal}>Cancel</Button>
          <Button color="red" onClick={handleDelete}>Delete</Button>
        </Group>
      </Modal>

      <Affix position={{ bottom: 20, right: 20 }}>
        <Transition transition="slide-up" mounted={!isOpen}>
          {(transitionStyles) => (
            <ActionIcon
              style={transitionStyles}
              onClick={toggleChat}
              size="xl"
              radius="xl"
              variant="filled"
              color="blue"
              h={60}
              w={60}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" style={{ width: 30, height: 30 }}>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </ActionIcon>
          )}
        </Transition>
      </Affix>

      <Affix position={chatPosition}>
        <Transition transition="slide-up" mounted={isOpen}>
          {(transitionStyles) => (
            <Card
              key={resetKey}
              style={{ ...transitionStyles, resize: 'both', overflow: 'hidden', display: 'flex', flexDirection: 'column', minWidth: 350, minHeight: 500 }}
              shadow="xl"
              padding="md"
              radius="md"
              withBorder
              w={600}
              h={700}
              maw="90vw"
              mah="90vh"
            >
              <Card.Section 
                withBorder 
                inheritPadding 
                py="xs" 
                bg="blue.6"
                onMouseDown={handleMouseDown}
                style={{ cursor: 'move' }}
              >
                <Group justify="space-between">
                  <Group>
                    {view === 'chat' && (
                      <ActionIcon variant="transparent" color="white" onClick={() => setView('list')}>
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" style={{ width: 20, height: 20 }}>
                          <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      </ActionIcon>
                    )}
                    <Text fw={700} c="white">Lenny Assistant</Text>
                  </Group>
                  <Group gap="xs">
                    <ActionIcon variant="transparent" color="white" onClick={handleResetPosition} title="Reset Position & Size">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" style={{ width: 20, height: 20 }}>
                            <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
                        </svg>
                    </ActionIcon>
                    <ActionIcon variant="transparent" color="white" onClick={toggleChat}>
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" style={{ width: 20, height: 20 }}>
                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                    </ActionIcon>
                  </Group>
                </Group>
              </Card.Section>

              {!characterId ? (
                <Stack align="center" justify="center" h="100%">
                  <Text>Please login to use the chat.</Text>
                </Stack>
              ) : view === 'list' ? (
                <Stack h="100%" pt="md">
                  <Button onClick={createConversation} loading={isLoading}>New Conversation</Button>
                  <ScrollArea flex={1}>
                    <Stack gap="xs">
                      {conversations.map(conv => (
                        <Group key={conv.id} wrap="nowrap" align="center">
                            <UnstyledButton 
                              onClick={() => loadConversation(conv.id)}
                              p="sm"
                              bg="gray.1"
                              style={{ borderRadius: 8, flex: 1 }}
                            >
                              <Text fw={500}>{conv.title || `Conversation ${conv.id}`}</Text>
                              <Text size="xs" c="dimmed">{new Date(conv.updated_at || conv.created_at).toLocaleString()}</Text>
                            </UnstyledButton>
                            <ActionIcon 
                                color="red" 
                                variant="subtle" 
                                onClick={(e) => confirmDelete(e, conv.id)}
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" style={{ width: 20, height: 20 }}>
                                  <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                                </svg>
                            </ActionIcon>
                        </Group>
                      ))}
                      {conversations.length === 0 && <Text c="dimmed" ta="center">No conversations yet.</Text>}
                    </Stack>
                  </ScrollArea>
                </Stack>
              ) : (
                <>
                  <ScrollArea flex={1} type="always" offsetScrollbars>
                    <Stack gap="xs" pt="md">
                      {messages.map((msg, index) => (
                        <Group key={index} justify={msg.role === 'user' ? 'flex-end' : 'flex-start'}>
                          <Card
                            padding="xs"
                            radius="md"
                            bg={msg.role === 'user' ? 'blue.6' : 'gray.1'}
                            c={msg.role === 'user' ? 'white' : 'black'}
                            maw="90%"
                            style={{ overflow: 'auto' }}
                          >
                            {msg.role === 'user' ? (
                              <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</Text>
                            ) : (
                              <div style={{ fontSize: '0.9rem' }}>
                                <ReactMarkdown 
                                  remarkPlugins={[remarkGfm]}
                                  components={MarkdownComponents}
                                >
                                  {msg.content}
                                </ReactMarkdown>
                              </div>
                            )}
                          </Card>
                        </Group>
                      ))}
                      {isLoading && (
                        <Group justify="flex-start">
                          <Card padding="xs" radius="md" bg="gray.1">
                            <Loader size="xs" type="dots" />
                          </Card>
                        </Group>
                      )}
                    </Stack>
                  </ScrollArea>

                  <Card.Section withBorder inheritPadding py="xs">
                    <form onSubmit={handleSubmit}>
                      <Group gap="xs">
                        <TextInput
                          placeholder="Ask about market data..."
                          value={input}
                          onChange={(e) => setInput(e.target.value)}
                          disabled={isLoading}
                          style={{ flex: 1 }}
                        />
                        <Button type="submit" disabled={isLoading || !input.trim()}>
                          Send
                        </Button>
                      </Group>
                    </form>
                  </Card.Section>
                </>
              )}
            </Card>
          )}
        </Transition>
      </Affix>
    </>
  );
};

export default ChatWidget;
