import { useEffect, useState } from "react";
import DropZone from "./components/DropZone";
import ThumbnailGrid from "./components/ThumbnailGrid";
import { SAMPLE_MEDIA } from "./data/mediaStub";

type StationId = "understand" | "curate" | "distill" | "apply";

interface Station {
  id: StationId;
  label: string;
  english: string;
}

const STATIONS: Station[] = [
  { id: "understand", label: "看懂", english: "Understand" },
  { id: "curate", label: "整理", english: "Curate" },
  { id: "distill", label: "鑄造", english: "Distill" },
  { id: "apply", label: "應用", english: "Apply" },
];

const App = (): React.JSX.Element => {
  const [version, setVersion] = useState<string>("讀取版本中");
  const [activeStation, setActiveStation] = useState<StationId>("understand");

  useEffect(() => {
    let isMounted = true;

    window.bridge.getAppVersion().then((appVersion) => {
      if (isMounted) {
        setVersion(appVersion);
      }
    });

    return () => {
      isMounted = false;
    };
  }, []);

  const active = STATIONS.find((station) => station.id === activeStation) ?? STATIONS[0];

  return (
    <main className="shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">VisionForge</p>
          <h1>資料工房</h1>
        </div>
        <p className="version">v{version}</p>
      </header>

      <nav className="station-nav" aria-label="核心迴圈">
        {STATIONS.map((station) => (
          <button
            type="button"
            key={station.id}
            className={station.id === activeStation ? "active" : ""}
            aria-pressed={station.id === activeStation}
            onClick={() => setActiveStation(station.id)}
          >
            <span>{station.label}</span>
            <small>{station.english}</small>
          </button>
        ))}
      </nav>

      <section className="workspace" aria-labelledby="station-title">
        <div className="section-heading">
          <p className="eyebrow">{active.english}</p>
          <h2 id="station-title">{active.label}</h2>
        </div>

        {activeStation === "understand" ? (
          <div className="understand-layout">
            <DropZone />
            <ThumbnailGrid media={SAMPLE_MEDIA} />
          </div>
        ) : (
          <div className="empty-panel">
            <p className="eyebrow">{active.english}</p>
            <h3>{active.label}施工中</h3>
          </div>
        )}
      </section>
    </main>
  );
};

export default App;
