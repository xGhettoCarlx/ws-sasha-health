/**
 * Standalone Trojan page kept as thin redirect target for old links.
 * Canonical UI lives on Insurance workspace via TrojanHorsePanel.
 */
import { Navigate } from "react-router-dom";

export default function TrojanHorsePage() {
  return <Navigate to="/insurance" replace />;
}
