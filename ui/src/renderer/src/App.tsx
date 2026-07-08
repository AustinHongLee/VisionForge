import { useEffect, useState } from "react";
import type { Claim, MediaRecord } from "../../shared/contracts.generated";
import { importFile, infer, listMedia, thumbnailUrl } from "./api/client";
import DetailView from "./components/DetailView";
import DropZone from "./components/DropZone";
import ThumbnailGrid from "./components/ThumbnailGrid";

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
  const [apiError, setApiError] = useState<string | null>(null);
  const [claimsByMedia, setClaimsByMedia] = useState<Record<string, Claim[]>>({});
  const [isInferring, setIsInferring] = useState(false);
  const [isLoadingMedia, setIsLoadingMedia] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [media, setMedia] = useState<MediaRecord[]>([]);
  const [pendingFiles, setPendingFiles] = useState<string[]>([]);
  const [selectedHash, setSelectedHash] = useState<string | null>(null);
  const [thumbnailUrls, setThumbnailUrls] = useState<Record<string, string>>({});

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

  const loadMedia = async (): Promise<void> => {
    setIsLoadingMedia(true);
    setApiError(null);
    try {
      const page = await listMedia();
      setMedia(page.items);
      setSelectedHash((current) => current ?? page.items[0]?.media_hash ?? null);
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

  const handleDetect = async (concepts: string[]): Promise<void> => {
    if (selectedMedia === null) {
      return;
    }
    setIsInferring(true);
    setApiError(null);
    try {
      const result = await infer(selectedMedia.media_hash, concepts);
      setClaimsByMedia((current) => ({
        ...current,
        [selectedMedia.media_hash]: result.claims,
      }));
    } catch (error) {
      setApiError(error instanceof Error ? error.message : String(error));
    } finally {
      setIsInferring(false);
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
            <div className="understand-left">
              <DropZone
                isUploading={isUploading}
                onFiles={(files) => {
                  void handleFiles(files);
                }}
                pendingFiles={pendingFiles}
              />
              {apiError !== null ? (
                <p className="error-message" role="alert">
                  {apiError}
                </p>
              ) : null}
              {isLoadingMedia ? <p className="muted">載入媒體中</p> : null}
              <ThumbnailGrid
                media={media}
                onSelect={(item) => setSelectedHash(item.media_hash)}
                selectedHash={selectedHash}
                thumbnailUrls={thumbnailUrls}
              />
            </div>
            <DetailView
              claims={selectedHash === null ? [] : (claimsByMedia[selectedHash] ?? [])}
              error={apiError}
              imageUrl={selectedHash === null ? undefined : thumbnailUrls[selectedHash]}
              isInferring={isInferring}
              media={selectedMedia}
              onDetect={(concepts) => {
                void handleDetect(concepts);
              }}
            />
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
