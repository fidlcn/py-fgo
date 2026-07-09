import { NavLink, Route, Routes } from "react-router-dom";
import { Dashboard } from "./pages/Dashboard";
import { Instances } from "./pages/Instances";
import { QuestProfiles } from "./pages/QuestProfiles";
import { SupportProfiles } from "./pages/SupportProfiles";
import { BattlePlans } from "./pages/BattlePlans";
import { Tasks } from "./pages/Tasks";
import { RunMonitor } from "./pages/RunMonitor";
import { LogsPage } from "./pages/Logs";
import { Settings } from "./pages/Settings";

const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/instances", label: "Instances" },
  { to: "/quests", label: "Quest Profiles" },
  { to: "/support", label: "Support Profiles" },
  { to: "/plans", label: "Battle Plans" },
  { to: "/tasks", label: "Tasks" },
  { to: "/monitor", label: "Run Monitor" },
  { to: "/logs", label: "Logs" },
  { to: "/settings", label: "Settings" },
];

export default function App() {
  return (
    <div className="app">
      <nav className="sidebar">
        <div className="brand">
          <span className="dot" /> FGO Bot
        </div>
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.end}
            className={({ isActive }) => "navlink" + (isActive ? " active" : "")}
          >
            {n.label}
          </NavLink>
        ))}
      </nav>
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/instances" element={<Instances />} />
          <Route path="/quests" element={<QuestProfiles />} />
          <Route path="/support" element={<SupportProfiles />} />
          <Route path="/plans" element={<BattlePlans />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/monitor" element={<RunMonitor />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
