import { Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion'; // eslint-disable-line no-unused-vars
import { ThemeProvider } from './context/ThemeContext';
import Sidebar from './components/Sidebar';
import Home from './pages/Home';
import Projects from './pages/Projects';
import ProjectWorkspace from './pages/ProjectWorkspace';
import Profile from './pages/Profile';
import History from './pages/History';
import NotFound from './pages/NotFound';
import MobileBottomNav from './components/MobileBottomNav';

function App() {
  const location = useLocation();

  return (
    <ThemeProvider>
      <div className="app-container">
        <Sidebar title="ResearchDoi" />
        <main className="main-content">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2, ease: "easeInOut" }}
              className="page-transition-wrapper"
            >
              <Routes location={location}>
                <Route path="/" element={<Home />} />
                <Route path="/projects" element={<Projects />} />
                <Route path="/projects/:projectId" element={<ProjectWorkspace />} />
                <Route path="/history" element={<History />} />
                <Route path="/profile" element={<Profile />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </motion.div>
          </AnimatePresence>
        </main>
        <MobileBottomNav />
      </div>
    </ThemeProvider>
  );
}

export default App;
