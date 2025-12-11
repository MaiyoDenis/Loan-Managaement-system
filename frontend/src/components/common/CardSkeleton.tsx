import React from 'react';
import { Card, CardContent, Skeleton, Stack } from '@mui/material';

interface CardSkeletonProps {
  count?: number;
}

const CardSkeleton: React.FC<CardSkeletonProps> = ({ count = 4 }) => {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <Card key={`skeleton-${index}`} elevation={1}>
          <CardContent>
            <Stack direction="row" spacing={2} alignItems="center">
              <Skeleton variant="circular" width={48} height={48} />
              <Stack spacing={1} sx={{ flexGrow: 1 }}>
                <Skeleton variant="text" width="40%" height={20} />
                <Skeleton variant="text" width="60%" height={32} />
              </Stack>
            </Stack>
          </CardContent>
        </Card>
      ))}
    </>
  );
};

export default CardSkeleton;