import { useEffect } from 'react';
import Navbar from './components/layout/Navbar';
import Footer from './components/layout/Footer';
import HistoryModal from './components/layout/HistoryModal';
import Home from './pages/Home';
import { pingHealth } from './services/api';
import useFileStore from './store/fileStore';
import useThemeStore from './store/useThemeStore';

export default function App() {
  const setPrewarmStatus = useFileStore((s) => s.setPrewarmStatus);
  const mode = useThemeStore((s) => s.mode);

  /**
   * Pre-warm the Render backend on app load.
   * Render free tier has ~30s cold start; pinging early prevents the first
   * upload from timing out.
   */
  useEffect(() => {
    if (mode === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
  }, [mode]);

  useEffect(() => {
    let cancelled = false;

    async function prewarm() {
      setPrewarmStatus('pinging');
      try {
        await pingHealth();
        if (!cancelled) setPrewarmStatus('ready');
      } catch {
        if (!cancelled) setPrewarmStatus('failed');
      }
    }

    prewarm();

    return () => { cancelled = true; };
  }, [setPrewarmStatus]);

  return (
    <div className="min-h-screen flex flex-col bg-surface-900">
      {/* Ambient background glow */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
        <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-primary-600/5 blur-[120px]" />
        <div className="absolute -bottom-40 -right-40 w-[500px] h-[500px] rounded-full bg-accent-600/5 blur-[100px]" />
      </div>

      <Navbar />

      <Home />

      <Footer />
      
      <HistoryModal />
    </div>
  );
}
