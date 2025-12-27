import React from 'react';
import { useRouter } from 'next/router';
import PageLayout from '../components/layout/PageLayout';
import ExperimentOverviewGrid from '../components/modules/experiment/ExperimentOverviewGrid';
import { DatabaseIcon } from '../components/ui/icons';

const IoTDashboard: React.FC = () => {
  const router = useRouter();

  const handleReferenceData = () => {
    router.push('/reference-management');
  };

  return (
    <PageLayout
      title="IoT Device Monitor"
      subtitle="Experiment Overview Dashboard"
      actions={
        <button
          onClick={handleReferenceData}
          className="button-responsive"
          style={{
            backgroundColor: 'var(--color-accent-blue)',
            color: 'var(--color-text-primary)',
            border: 'none',
            cursor: 'pointer',
            fontWeight: '500',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 'var(--spacing-sm)',
            fontSize: 'var(--text-base)',
            transition: 'all 0.2s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--color-accent-blue-dark, #1d4ed8)';
            e.currentTarget.style.boxShadow = 'var(--shadow-md)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--color-accent-blue)';
            e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
          }}
        >
          <DatabaseIcon size={20} color="white" />
          Reference Data
        </button>
      }
    >
      <ExperimentOverviewGrid />
    </PageLayout>
  );
};

export default IoTDashboard; 