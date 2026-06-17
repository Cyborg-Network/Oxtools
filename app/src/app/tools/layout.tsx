import { SidebarInset, SidebarProvider, SidebarTrigger } from "@ansospace/ui";

import { AppSidebar } from "@/components/tools/app-sidebar";
import { AuthProvider } from "@/providers/auth-provider";

export default function ToolsLayout({ children }: { children: React.ReactNode }) {
	return (
		<AuthProvider>
			<SidebarProvider>
				<AppSidebar />
				<SidebarInset>
					{/* Minimal header - just the sidebar trigger, no redundant "Oxtools" text */}
					<header className="sticky top-0 z-10 flex h-10 items-center border-b border-border/50 bg-background/80 px-3 backdrop-blur-sm">
						<SidebarTrigger className="-ml-1" />
					</header>
					<main className="flex-1">{children}</main>
				</SidebarInset>
			</SidebarProvider>
		</AuthProvider>
	);
}
