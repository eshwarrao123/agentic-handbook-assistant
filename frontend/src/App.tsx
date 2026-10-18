/**
 * App.tsx — root component.
 * Renders the ChatPage as the entire application.
 * The diagnostic health dashboard from Phase 1 has been superseded by
 * the connection status indicator inside ChatPage.
 */

import { ChatPage } from './components/ChatPage';
import './App.css';

export default function App() {
  return <ChatPage />;
}
