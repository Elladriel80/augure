import { redirect } from "next/navigation";

// /algorithm has been renamed to /predictor. This page is kept as a
// permanent redirect so any external bookmarks or links still resolve.
export default function AlgorithmRedirect() {
  redirect("/predictor");
}
