import React, { useState, useEffect } from 'react';
import { 
  Container, 
  Title, 
  Card, 
  Text, 
  Button, 
  Group, 
  Table,
  TextInput,
  ActionIcon,
  Badge,
  Modal,
  Select,
  Tabs
} from '@mantine/core';
import { IconSearch, IconPlus, IconEdit, IconTrash, IconRefresh } from '@tabler/icons-react';
import { api } from '../utils/api';

const RFIDManagement = () => {
  const [tags, setTags] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [currentTag, setCurrentTag] = useState(null);
  const [activeTab, setActiveTab] = useState('people');

  // Form state
  const [formData, setFormData] = useState({
    tagId: '',
    type: 'person',
    assignedTo: '',
    status: 'active'
  });

  useEffect(() => {
    fetchTags();
  }, [activeTab]);

  const fetchTags = async () => {
    try {
      setIsLoading(true);
      // In a real app, this would be a call to your API
      // const response = await api.get(`/rfid/tags?type=${activeTab === 'people' ? 'person' : 'product'}`);
      
      // Simulated data for now
      setTimeout(() => {
        const mockTags = activeTab === 'people' 
          ? [
              { id: 1, tagId: 'RFID001', type: 'person', assignedTo: 'John Doe', status: 'active', lastSeen: '2025-03-12T14:32:00Z' },
              { id: 2, tagId: 'RFID002', type: 'person', assignedTo: 'Jane Smith', status: 'active', lastSeen: '2025-03-13T09:15:00Z' },
              { id: 3, tagId: 'RFID003', type: 'person', assignedTo: 'Mike Johnson', status: 'inactive', lastSeen: '2025-02-28T11:45:00Z' }
            ]
          : [
              { id: 4, tagId: 'RFID101', type: 'product', assignedTo: 'Laptop Dell XPS', status: 'active', lastSeen: '2025-03-14T06:22:00Z' },
              { id: 5, tagId: 'RFID102', type: 'product', assignedTo: 'Monitor LG 27"', status: 'active', lastSeen: '2025-03-10T15:40:00Z' },
              { id: 6, tagId: 'RFID103', type: 'product', assignedTo: 'Keyboard Logitech', status: 'inactive', lastSeen: '2025-03-05T08:12:00Z' }
            ];
            
        setTags(mockTags);
        setIsLoading(false);
      }, 600);
    } catch (error) {
      console.error('Failed to fetch RFID tags:', error);
      setIsLoading(false);
    }
  };

  const handleSearch = (e) => {
    setSearchQuery(e.target.value);
  };

  const filteredTags = tags.filter(tag => 
    tag.tagId.toLowerCase().includes(searchQuery.toLowerCase()) ||
    tag.assignedTo.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleOpenModal = (tag = null) => {
    if (tag) {
      setCurrentTag(tag);
      setFormData({
        tagId: tag.tagId,
        type: tag.type,
        assignedTo: tag.assignedTo,
        status: tag.status
      });
    } else {
      setCurrentTag(null);
      setFormData({
        tagId: '',
        type: activeTab === 'people' ? 'person' : 'product',
        assignedTo: '',
        status: 'active'
      });
    }
    setModalOpen(true);
  };

  const handleFormChange = (field, value) => {
    setFormData({
      ...formData,
      [field]: value
    });
  };

  const handleSubmit = async () => {
    try {
      if (currentTag) {
        // Update existing tag
        // await api.put(`/rfid/tags/${currentTag.id}`, formData);
        console.log('Updating tag:', currentTag.id, formData);
        
        // Update local state
        setTags(tags.map(tag => 
          tag.id === currentTag.id ? { ...tag, ...formData } : tag
        ));
      } else {
        // Create new tag
        // const response = await api.post('/rfid/tags', formData);
        console.log('Creating new tag:', formData);
        
        // Add to local state with a fake ID
        const newTag = {
          id: Math.floor(Math.random() * 1000),
          ...formData,
          lastSeen: new Date().toISOString()
        };
        setTags([...tags, newTag]);
      }
      
      setModalOpen(false);
    } catch (error) {
      console.error('Failed to save RFID tag:', error);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this RFID tag?')) {
      return;
    }
    
    try {
      // await api.delete(`/rfid/tags/${id}`);
      console.log('Deleting tag:', id);
      
      // Remove from local state
      setTags(tags.filter(tag => tag.id !== id));
    } catch (error) {
      console.error('Failed to delete RFID tag:', error);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  return (
    <Container size="lg" py="xl">
      <Title order={2} mb="xl">RFID Management</Title>
      
      <Tabs value={activeTab} onTabChange={setActiveTab} mb="xl">
        <Tabs.List>
          <Tabs.Tab value="people" icon={<IconUsers size={14} />}>
            People Tags
          </Tabs.Tab>
          <Tabs.Tab value="products" icon={<IconPackage size={14} />}>
            Product Tags
          </Tabs.Tab>
        </Tabs.List>
      </Tabs>
      
      <Card withBorder p="md" radius="md" mb="xl">
        <Group position="apart" mb="md">
          <TextInput
            placeholder="Search tags or assignments..."
            icon={<IconSearch size={16} />}
            value={searchQuery}
            onChange={handleSearch}
            style={{ width: '60%' }}
          />
          <Group>
            <Button 
              leftIcon={<IconRefresh size={16} />} 
              variant="outline"
              onClick={fetchTags}
              loading={isLoading}
            >
              Refresh
            </Button>
            <Button 
              leftIcon={<IconPlus size={16} />} 
              onClick={() => handleOpenModal()}
            >
              Add New Tag
            </Button>
          </Group>
        </Group>
        
        {isLoading ? (
          <Text align="center" py="md">Loading RFID tags...</Text>
        ) : (
          <Table striped highlightOnHover>
            <thead>
              <tr>
                <th>Tag ID</th>
                <th>Assigned To</th>
                <th>Status</th>
                <th>Last Seen</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredTags.length > 0 ? (
                filteredTags.map((tag) => (
                  <tr key={tag.id}>
                    <td>{tag.tagId}</td>
                    <td>{tag.assignedTo}</td>
                    <td>
                      <Badge 
                        color={tag.status === 'active' ? 'green' : 'gray'}
                      >
                        {tag.status}
                      </Badge>
                    </td>
                    <td>{formatDate(tag.lastSeen)}</td>
                    <td>
                      <Group spacing={4}>
                        <ActionIcon color="blue" onClick={() => handleOpenModal(tag)}>
                          <IconEdit size={18} />
                        </ActionIcon>
                        <ActionIcon color="red" onClick={() => handleDelete(tag.id)}>
                          <IconTrash size={18} />
                        </ActionIcon>
                      </Group>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5}>
                    <Text align="center" color="dimmed" py="md">
                      No RFID tags found. Add a new tag to get started.
                    </Text>
                  </td>
                </tr>
              )}
            </tbody>
          </Table>
        )}
      </Card>
      
      <Modal
        opened={modalOpen}
        onClose={() => setModalOpen(false)}
        title={currentTag ? "Edit RFID Tag" : "Add New RFID Tag"}
      >
        <TextInput
          label="Tag ID"
          placeholder="Enter RFID tag ID"
          value={formData.tagId}
          onChange={(e) => handleFormChange('tagId', e.target.value)}
          required
          mb="md"
        />
        
        <Select
          label="Type"
          data={[
            { value: 'person', label: 'Person' },
            { value: 'product', label: 'Product' }
          ]}
          value={formData.type}
          onChange={(value) => handleFormChange('type', value)}
          mb="md"
        />
        
        <TextInput
          label="Assigned To"
          placeholder="Person name or product description"
          value={formData.assignedTo}
          onChange={(e) => handleFormChange('assignedTo', e.target.value)}
          mb="md"
        />
        
        <Select
          label="Status"
          data={[
            { value: 'active', label: 'Active' },
            { value: 'inactive', label: 'Inactive' }
          ]}
          value={formData.status}
          onChange={(value) => handleFormChange('status', value)}
          mb="xl"
        />
        
        <Group position="right">
          <Button variant="outline" onClick={() => setModalOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit}>
            {currentTag ? 'Update' : 'Create'}
          </Button>
        </Group>
      </Modal>
    </Container>
  );
};

export default RFIDManagement;
