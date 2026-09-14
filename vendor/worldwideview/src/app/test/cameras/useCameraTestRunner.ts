import {
 useState, useRef, useEffect, useCallback
} from "react";
import type { TestResult } from "./types";
import type { GdotCameraFeature } from "@/app/api/camera/gdot/gdotFetcher";

export function useCameraTestRunner(testSources: string[], testStatuses: string[]) {
    const [cameras, setCameras] = useState<TestResult[]>([]);
    const [loading, setLoading] = useState(false);
    const [testing, setTesting] = useState(false);
    const abortControllerRef = useRef<AbortController | null>(null);

    const fetchCameras = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch("/api/camera/traffic");
            const data = await res.json();

            let staticFeatures: GdotCameraFeature[] = [];
            try {
                const staticRes = await fetch("/public-cameras.json");
                if (staticRes.ok) {
                    const staticData = await staticRes.json();
                    if (staticData.features) {
                        staticFeatures = staticData.features.map((f: Record<string, unknown>) => {
                            const props = (f.properties || {}) as Record<string, unknown>;
                            return {
                                ...f,
                                properties: {
                                    ...props,
                                    name: props.city || props.region || "Public Camera",
                                    source: props.source || "cameras_json"
                                }
                            } as unknown as GdotCameraFeature;
                        });
                    }
                }
            } catch (staticErr) {
                void staticErr; // Ignore static fetch errors
            }

            let combinedFeatures: GdotCameraFeature[] = [];
            if (data.cameras) {
                combinedFeatures = [...data.cameras];
            }
            combinedFeatures = [...combinedFeatures, ...staticFeatures];

            setCameras(combinedFeatures.map((c: GdotCameraFeature) => ({
                feature: c,
                status: "pending"
            })));
        } catch (err) {
            void err; // Ignore errors
        }
        setLoading(false);
    }, []);

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        void fetchCameras();
    }, [fetchCameras]);

    const runTests = async () => {
        if (testing) return;
        setTesting(true);

        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        abortControllerRef.current = new AbortController();
        const {signal} = abortControllerRef.current;

        const maxConcurrent = 20;
        let index = 0;
        let active = 0;

        const itemsToTest = cameras
            .map((c, originalIndex) => ({ c, originalIndex }))
            .filter(({ c }) => {
                const sourceMatches = testSources.includes("all") || testSources.includes(c.feature.properties.source || "Unknown");
                const statusMatches = testStatuses.includes("all") || testStatuses.includes(c.status);
                return sourceMatches && statusMatches;
            });

        setCameras((prev) => {
            const nextState = [...prev];
            for (const { originalIndex } of itemsToTest) {
                nextState[originalIndex] = {
 ...nextState[originalIndex], status: "pending", testStartTime: undefined, latencyMs: undefined, errorMsg: undefined, httpStatus: undefined, contentType: undefined
};
            }
            return nextState;
        });

        await new Promise<void>((resolve) => {
            const next = () => {
                if (signal.aborted) {
                    resolve();
                    return;
                }
                while (active < maxConcurrent && index < itemsToTest.length) {
                    const item = itemsToTest[index];
                    index += 1;
                    const currentIndex = item.originalIndex;
                    active += 1;

                    const cam = item.c;
                    const streamUrl = cam.feature.properties.stream;

                    if (!streamUrl) {
                        setCameras((prev) => {
                            const nextState = [...prev];
                            nextState[currentIndex] = {
                                ...nextState[currentIndex],
                                status: "error",
                                errorMsg: "No stream URL provided"
                            };
                            return nextState;
                        });
                        active -= 1;
                        next();
                        continue;
                    }

                    setCameras((prev) => {
                        const nextState = [...prev];
                        nextState[currentIndex] = { ...nextState[currentIndex], status: "testing", testStartTime: Date.now() };
                        return nextState;
                    });

                    fetch(`/api/camera/test?url=${encodeURIComponent(streamUrl)}`, { signal })
                        .then((res) => res.json())
                        .then((data) => {
                            setCameras((prev) => {
                                const nextState = [...prev];
                                const isOk = data.status === 200 || data.status === 204 || data.status === 206;
                                nextState[currentIndex] = {
                                    ...nextState[currentIndex],
                                    status: isOk ? "ok" : (data.status === "timeout" ? "timeout" : "error"),
                                    httpStatus: data.status,
                                    contentType: data.contentType,
                                    latencyMs: data.latencyMs,
                                    errorMsg: data.error
                                };
                                return nextState;
                            });
                        })
                        .catch((err) => {
                            if (err.name === 'AbortError') return;
                            setCameras((prev) => {
                                const nextState = [...prev];
                                nextState[currentIndex] = {
                                    ...nextState[currentIndex],
                                    status: "error",
                                    errorMsg: err.message
                                };
                                return nextState;
                            });
                        })
                        .finally(() => {
                            active -= 1;
                            next();
                        });
                }

                if (active === 0 && index >= itemsToTest.length) {
                    resolve();
                }
            };
            next();
        });

        setTesting(false);
    };

    const stopTests = () => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            setTesting(false);
        }
    };

    const retestCamera = async (globalIndex: number) => {
        const cam = cameras[globalIndex];
        const streamUrl = cam.feature.properties.stream;
        if (!streamUrl) return;

        setCameras((prev) => {
            const nextState = [...prev];
            nextState[globalIndex] = {
 ...nextState[globalIndex], status: "testing", testStartTime: Date.now(), latencyMs: undefined, errorMsg: undefined, httpStatus: undefined, contentType: undefined
};
            return nextState;
        });

        try {
            const res = await fetch(`/api/camera/test?url=${encodeURIComponent(streamUrl)}`);
            const data = await res.json();
            setCameras((prev) => {
                const nextState = [...prev];
                const isOk = data.status === 200 || data.status === 204 || data.status === 206;
                nextState[globalIndex] = {
                    ...nextState[globalIndex],
                    status: isOk ? "ok" : (data.status === "timeout" ? "timeout" : "error"),
                    httpStatus: data.status,
                    contentType: data.contentType,
                    latencyMs: data.latencyMs,
                    errorMsg: data.error
                };
                return nextState;
            });
        } catch (err: unknown) {
            const errorMsg = err instanceof Error ? err.message : String(err);
            setCameras((prev) => {
                const nextState = [...prev];
                nextState[globalIndex] = {
                    ...nextState[globalIndex],
                    status: "error",
                    errorMsg
                };
                return nextState;
            });
        }
    };

    return {
 cameras, loading, testing, runTests, stopTests, retestCamera
};
}
