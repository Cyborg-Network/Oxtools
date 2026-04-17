import { redirect } from "next/navigation";

/**
 * Root page redirects directly to the tools dashboard.
 * Manager directive: no landing page, users go straight to tools.
 */
export default function HomePage() {
	redirect("/tools");
}
