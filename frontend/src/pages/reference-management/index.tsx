import React from 'react';
import { ReferenceDataViewer } from '../../components/modules/reference';

const ReferenceManagementPage: React.FC = () => {
  return (
    <div style={{ 
      minHeight: '100vh',
      backgroundColor: 'var(--color-bg-primary)'
    }}>
      <ReferenceDataViewer />
    </div>
  );
};

export default ReferenceManagementPage; 