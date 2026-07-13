import { useEffect, useState } from "react";
import type { MediaRecord } from "../../shared/contracts.generated";
import { importFile, listMedia, thumbnailUrl } from "./api/client";
import ApplyView from "./components/ApplyView";
import DistillView from "./components/DistillView";
import DropZone from "./components/DropZone";
import ReleaseView from "./components/ReleaseView";
import TeachingView from "./components/TeachingView";
import ThumbnailGrid from "./components/ThumbnailGrid";

type StationId = "teach" | "distill" | "releases" | "apply";

interface Station {
  id: StationId;
  label: string;
  english: string;
}

const STATIONS: Station[] = [
  { id: "teach", label: "教學", english: "Teach" },
  { id: "distill", label: "鑄造", english: "Distill" },
  { id: "releases", label: "版本", english: "Releases" },
  { id: "apply", label: "應用", english: "Apply" },
];

const App = (): React.JSX.Element => {
  const [version, setVersion] = useState<string>("讀取版本中");
  const [activeStation, setActiveStation] = useState<StationId>("teach");
  const [apiError, setApiError] = useState<string | null>(null);
  const [isLoadingMedia, setIsLoadingMedia] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [media, setMedia] = useState<MediaRecord[]>([]);
  const [pendingFiles, setPendingFiles] = useState<string[]>([]);
  const [selectedHash, setSelectedHash] = useState<string | null>(null);
  const [thumbnailUrls, setThumbnailUrls] = useState<Record<string, string>>({});
  const [projectPath, setProjectPath] = useState("讀取 Project 中");
  const [isSwitchingProject, setIsSwitchingProject] = useState(false);
  const [projectEpoch, setProjectEpoch] = useState(0);

  useEffect(() => {
    let isMounted = true;

    window.bridge.getAppVersion().then((appVersion) => {
      if (isMounted) {
        setVersion(appVersion);
      }
    });
    window.bridge.getProjectPath().then((path) => {
      if (isMounted) {
        setProjectPath(path);
      }
    });

    return () => {
      isMounted = false;
    };
  }, []);

  const loadMedia = async (resetSelection = false): Promise<void> => {
    setIsLoadingMedia(true);
    setApiError(null);
    try {
      const page = await listMedia();
      setMedia(page.items);
      setSelectedHash((current) =>
        resetSelection ? (page.items[0]?.media_hash ?? null) : (current ?? page.items[0]?.media_hash ?? null),
      );
      const entries = await Promise.all(
        page.items.map(async (item) => [item.media_hash, await thumbnailUrl(item.media_hash)] as const),
      );
      setThumbnailUrls(Object.fromEntries(entries));
    } catch (error) {
      setApiError(error instanceof Error ? error.message : String(error));
    } finally {
      setIsLoadingMedia(false);
    }
  };

  useEffect(() => {
    void loadMedia();
  }, []);

  const selectedMedia = media.find((item) => item.media_hash === selectedHash) ?? null;

  const chooseProject = async (): Promise<void> => {
    const path = await window.bridge.pickDirectory();
    if (path === null) return;
    setIsSwitchingProject(true);
    setApiError(null);
    try {
      await window.bridge.switchProject(path);
      setProjectPath(path);
      setPendingFiles([]);
      await loadMedia(true);
      setProjectEpoch((current) => current + 1);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : String(error));
    } finally {
      setIsSwitchingProject(false);
    }
  };

  const handleFiles = async (files: File[]): Promise<void> => {
    if (files.length === 0) {
      return;
    }
    setPendingFiles(files.map((file) => file.name));
    setIsUploading(true);
    setApiError(null);
    try {
      await Promise.all(files.map((file) => importFile(file)));
      await loadMedia();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : String(error));
    } finally {
      setIsUploading(false);
    }
  };

  const active = STATIONS.find((station) => station.id === activeStation) ?? STATIONS[0];

  return (
    <main className="shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">VisionForge</p>
          <h1>資料工房</h1>
        </div>
        <div className="project-control">
          <span title={projectPath}>{projectPath}</span>
          <button
            className="secondary-action"
            disabled={isSwitchingProject}
            type="button"
            onClick={() => void chooseProject()}
          >
            {isSwitchingProject ? "切換中" : "建立／開啟 Project"}
          </button>
          <small>空資料夾會建立；既有 VisionForge 資料夾會開啟</small>
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
        {apiError !== null ? (
          <p className="error-message" role="alert">
            {apiError}
          </p>
        ) : null}

        {activeStation === "teach" ? (
          <div className="understand-layout">
            <div className="understand-left">
              <DropZone
                isUploading={isUploading}
                onFiles={(files) => {
                  void handleFiles(files);
                }}
                pendingFiles={pendingFiles}
              />
              {isLoadingMedia ? <p className="muted">載入媒體中</p> : null}
              <ThumbnailGrid
                media={media}
                onSelect={(item) => setSelectedHash(item.media_hash)}
                selectedHash={selectedHash}
                thumbnailUrls={thumbnailUrls}
              />
            </div>
            <TeachingView
              key={projectEpoch}
              imageUrl={selectedHash === null ? undefined : thumbnailUrls[selectedHash]}
              media={selectedMedia}
              onError={setApiError}
            />
          </div>
        ) : activeStation === "distill" ? (
          <DistillView key={projectEpoch} onError={setApiError} />
        ) : activeStation === "apply" ? (
          <ApplyView key={projectEpoch} onError={setApiError} />
        ) : activeStation === "releases" ? (
          <ReleaseView key={projectEpoch} onError={setApiError} />
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
