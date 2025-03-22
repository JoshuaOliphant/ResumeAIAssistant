import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Box, Button, CircularProgress, Paper, Switch, Typography, FormControlLabel } from '@mui/material';
import { styled } from '@mui/material/styles';

// Styled components for diff view
const DiffContainer = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  marginTop: theme.spacing(2),
  marginBottom: theme.spacing(2),
  '& .addition': {
    backgroundColor: '#e6ffed',
    color: '#22863a',
  },
  '& .deletion': {
    backgroundColor: '#ffeef0',
    color: '#cb2431',
    textDecoration: 'line-through',
  },
  '& .modification': {
    backgroundColor: '#fff5b1',
  }
}));

const StatsContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  justifyContent: 'space-between',
  marginBottom: theme.spacing(2),
  padding: theme.spacing(2),
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.shape.borderRadius,
}));

const StatItem = styled(Box)(({ theme }) => ({
  textAlign: 'center',
  padding: theme.spacing(1),
}));

/**
 * Component to display a diff view of a customized resume
 */
const ResumeDiffView = ({ resumeId, versionId, originalVersionId }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [diffData, setDiffData] = useState(null);
  const [showDiff, setShowDiff] = useState(true);

  useEffect(() => {
    const fetchDiffData = async () => {
      setLoading(true);
      try {
        // Build URL with optional originalVersionId
        let url = `/api/v1/resumes/${resumeId}/versions/${versionId}/diff`;
        if (originalVersionId) {
          url += `?original_version_id=${originalVersionId}`;
        }
        
        const response = await axios.get(url);
        setDiffData(response.data);
        setError(null);
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to load diff view');
        console.error('Error fetching diff data:', err);
      } finally {
        setLoading(false);
      }
    };

    if (resumeId && versionId) {
      fetchDiffData();
    }
  }, [resumeId, versionId, originalVersionId]);

  const handleToggleChange = () => {
    setShowDiff(!showDiff);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" my={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box my={2}>
        <Typography color="error">{error}</Typography>
      </Box>
    );
  }

  if (!diffData) {
    return null;
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5">{diffData.title}</Typography>
        <FormControlLabel
          control={
            <Switch
              checked={showDiff}
              onChange={handleToggleChange}
              color="primary"
            />
          }
          label="Show Changes"
        />
      </Box>

      {showDiff && diffData.diff_statistics && (
        <StatsContainer>
          <StatItem>
            <Typography variant="body2" color="textSecondary">Additions</Typography>
            <Typography variant="h6" color="success.main">
              +{diffData.diff_statistics.additions}
            </Typography>
          </StatItem>
          <StatItem>
            <Typography variant="body2" color="textSecondary">Deletions</Typography>
            <Typography variant="h6" color="error.main">
              -{diffData.diff_statistics.deletions}
            </Typography>
          </StatItem>
          <StatItem>
            <Typography variant="body2" color="textSecondary">Modifications</Typography>
            <Typography variant="h6" color="warning.main">
              {diffData.diff_statistics.modifications}
            </Typography>
          </StatItem>
          <StatItem>
            <Typography variant="body2" color="textSecondary">Unchanged</Typography>
            <Typography variant="h6" color="info.main">
              {diffData.diff_statistics.unchanged}
            </Typography>
          </StatItem>
        </StatsContainer>
      )}

      <DiffContainer>
        {showDiff ? (
          <div dangerouslySetInnerHTML={{ __html: diffData.diff_content }} />
        ) : (
          <div>{diffData.customized_content}</div>
        )}
      </DiffContainer>
    </Box>
  );
};

export default ResumeDiffView;
