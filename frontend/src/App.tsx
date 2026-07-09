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
import { Calibration } from "./pages/Calibration";

const NAV = [
  { to: "/", label: "首页", end: true },
  { to: "/instances", label: "模拟器" },
  { to: "/quests", label: "关卡配置" },
  { to: "/support", label: "助战配置" },
  { to: "/plans", label: "战斗方案" },
  { to: "/tasks", label: "任务" },
  { to: "/monitor", label: "运行监控" },
  { to: "/calibration", label: "坐标校准" },
  { to: "/logs", label: "日志" },
  { to: "/settings", label: "设置" },
];

export default function App() {
  return (
    <div className="app">
      <nav className="sidebar">
        <div className="brand">
          <span className="dot" /> FGO 助手
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
          <Route path="/calibration" element={<Calibration />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
