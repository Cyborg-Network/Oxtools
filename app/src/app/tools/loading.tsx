import { Spinner } from "@ansospace/ui";

export default function Loading() {
  return (
    <div className="flex items-center justify-center p-12">
      <Spinner className="h-8 w-8 text-primary" />
    </div>
  );
}
