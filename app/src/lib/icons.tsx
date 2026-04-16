import {
  Bug,
  Shield,
  FlaskConical,
  GitPullRequest,
  Code2,
  Database,
  Zap,
  Wand2,
  Search,
  FileText,
  PenLine,
  GitFork,
  Palette,
  Camera,
  Terminal,
  BarChart3,
  Table2,
  BookOpen,
  Regex,
  Type,
  FileSearch,
  MonitorSmartphone,
  Globe,
  PenTool,
  Server,
  Home,
} from "lucide-react";
import type { ReactNode } from "react";

/**
 * Maps Lucide icon names to React components.
 * Used across the sidebar, tool cards, and tool page headers.
 *
 * When adding a new tool, add its icon name here.
 */
const iconMap: Record<string, (props: { className?: string }) => ReactNode> = {
  Bug: (p) => <Bug {...p} />,
  Shield: (p) => <Shield {...p} />,
  FlaskConical: (p) => <FlaskConical {...p} />,
  GitPullRequest: (p) => <GitPullRequest {...p} />,
  Code2: (p) => <Code2 {...p} />,
  Database: (p) => <Database {...p} />,
  Zap: (p) => <Zap {...p} />,
  Wand2: (p) => <Wand2 {...p} />,
  Search: (p) => <Search {...p} />,
  FileText: (p) => <FileText {...p} />,
  PenLine: (p) => <PenLine {...p} />,
  GitFork: (p) => <GitFork {...p} />,
  Palette: (p) => <Palette {...p} />,
  Camera: (p) => <Camera {...p} />,
  Terminal: (p) => <Terminal {...p} />,
  BarChart3: (p) => <BarChart3 {...p} />,
  Table2: (p) => <Table2 {...p} />,
  BookOpen: (p) => <BookOpen {...p} />,
  Regex: (p) => <Regex {...p} />,
  Type: (p) => <Type {...p} />,
  FileSearch: (p) => <FileSearch {...p} />,
  MonitorSmartphone: (p) => <MonitorSmartphone {...p} />,
  Globe: (p) => <Globe {...p} />,
  PenTool: (p) => <PenTool {...p} />,
  Server: (p) => <Server {...p} />,
  Home: (p) => <Home {...p} />,
};

/**
 * Get a Lucide icon component by name.
 * Falls back to Code2 if name not found.
 */
export function getToolIcon(name: string, className?: string): ReactNode {
  const factory = iconMap[name];
  if (factory) return factory({ className });
  // Fallback
  return <Code2 className={className} />;
}
