/* ==========================================================================
   VeriQuest — Main Application Shell
   ========================================================================== */

import React, { useState } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { AppSidebar } from './components/layout/AppSidebar';
import { TopHeader } from './components/layout/TopHeader';
import { MobileNav } from './components/layout/MobileNav';
import { ToastContainer } from './components/common/Toast';
import { AuthModal } from './components/auth/AuthModal';

import { DashboardView } from './views/DashboardView';
import { RoadmapView } from './views/RoadmapView';
import { ChallengesView } from './views/ChallengesView';
import { WorkspaceView } from './views/WorkspaceView';
import { QuestsView } from './views/QuestsView';
import { AchievementsView } from './views/AchievementsView';
import { LeaderboardView } from './views/LeaderboardView';
import { ProfileView } from './views/ProfileView';
import { SettingsView } from './views/SettingsView';
import { AdminView } from './views/AdminView';

const AppContent: React.FC = () => {
  const { currentRoute } = useApp();
  const [isMobileMenuOpen, setMobileMenuOpen] = useState(false);

  const renderActiveView = () => {
    switch (currentRoute) {
      case 'dashboard':
        return <DashboardView />;
      case 'learn':
        return <RoadmapView />;
      case 'challenges':
        return <ChallengesView />;
      case 'workspace':
        return <WorkspaceView />;
      case 'quests':
        return <QuestsView />;
      case 'leaderboard':
        return <LeaderboardView />;
      case 'achievements':
        return <AchievementsView />;
      case 'profile':
        return <ProfileView />;
      case 'settings':
        return <SettingsView />;
      case 'admin':
        return <AdminView />;
      default:
        return <DashboardView />;
    }
  };

  return (
    <div className="app-container">
      {/* Desktop Persistent Left Sidebar */}
      <AppSidebar />

      {/* Mobile Drawer */}
      <MobileNav isOpen={isMobileMenuOpen} onClose={() => setMobileMenuOpen(false)} />

      {/* Main Viewport */}
      <div className="app-main">
        <TopHeader onMobileToggle={() => setMobileMenuOpen(true)} />

        <main className="page-container" style={{ padding: currentRoute === 'workspace' ? '12px 16px' : undefined }}>
          {renderActiveView()}
        </main>
      </div>

      {/* Overlays */}
      <ToastContainer />
      <AuthModal />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
};

export default App;
