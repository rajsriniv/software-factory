import React from "react";
import { createRoot } from "react-dom/client";

function App() { return <main><h1>Software Factory</h1><p>Reference frontend</p></main>; }
createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);

