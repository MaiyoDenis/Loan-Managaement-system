import React, { useEffect, useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Stack,
  List,
  ListItem,
  ListItemText,
  Chip,
  Button,
  Divider,
} from '@mui/material';
import { useApiError } from '../../hooks/useApiError';
import { getNotifications, markAsRead, type NotificationItem } from '../../services/notificationService';

const typeToColor: Record<NotificationItem['type'], 'default' | 'primary' | 'success' | 'warning' | 'error'> = {
  info: 'primary',
  success: 'success',
  warning: 'warning',
  error: 'error',
};

const NotificationCenter: React.FC = () => {
  const { showError } = useApiError();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getNotifications();
        setItems(data);
      } catch (err) {
        showError(err as Error);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [showError]);

  const handleMarkRead = async (id: string) => {
    try {
      await markAsRead(id);
      setItems((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
    } catch (err) {
      showError(err as Error);
    }
  };

  if (loading) {
    return (
      <Card elevation={1}>
        <CardContent>
          <Typography variant="body2" color="text.secondary">
            Loading notifications...
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card elevation={1}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6">Notifications</Typography>
          <Chip label={`${items.filter((n) => !n.read).length} unread`} color="primary" size="small" />
        </Stack>

        {items.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            You’re all caught up.
          </Typography>
        ) : (
          <List disablePadding>
            {items.map((n, idx) => (
              <React.Fragment key={n.id}>
                <ListItem
                  secondaryAction={
                    !n.read ? (
                      <Button size="small" variant="text" onClick={() => handleMarkRead(n.id)}>
                        Mark read
                      </Button>
                    ) : null
                  }
                >
                  <ListItemText
                    primary={
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Chip label={n.type} color={typeToColor[n.type]} size="small" />
                        <Typography variant="body1">{n.message}</Typography>
                      </Stack>
                    }
                    secondary={n.created_at ? new Date(n.created_at).toLocaleString() : undefined}
                  />
                </ListItem>
                {idx < items.length - 1 && <Divider component="li" />}
              </React.Fragment>
            ))}
          </List>
        )}
      </CardContent>
    </Card>
  );
};

export default NotificationCenter;
