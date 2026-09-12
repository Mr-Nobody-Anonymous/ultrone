import type { FC } from 'react';
import { useState, useRef, useEffect } from 'react';
import { Camera, Video, Image, Play, Square, Download, Scan } from 'lucide-react';

interface CameraFrame {
  id: string;
  timestamp: string;
  source: string;
  type: 'sensor' | 'satellite' | 'drone' | 'thermal';
  confidence: number;
  objects: Array<{ label: string; bbox: [number, number, number, number]; confidence: number }>;
}

const CameraFeed: FC = () => {
  const [isActive, setIsActive] = useState(false);
  const [capturedFrames, setCapturedFrames] = useState<CameraFrame[]>([]);
  const [activeSource, setActiveSource] = useState('sensor');
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

  useEffect(() => {
    if (!isActive || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let frame = 0;
    const animate = () => {
      frame++;
      ctx.fillStyle = '#0a0f1a';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Simulated radar sweep
      ctx.strokeStyle = '#22c55e';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(160, 120, 80, 0, Math.PI * 2);
      ctx.stroke();

      const angle = (frame % 360) * (Math.PI / 180);
      ctx.strokeStyle = 'rgba(34, 197, 94, 0.3)';
      ctx.beginPath();
      ctx.moveTo(160, 120);
      ctx.lineTo(160 + Math.cos(angle) * 80, 120 + Math.sin(angle) * 80);
      ctx.stroke();

      // Blips
      if (frame % 30 === 0) {
        const bx = 160 + Math.random() * 60 - 30;
        const by = 120 + Math.random() * 60 - 30;
        ctx.fillStyle = '#ef4444';
        ctx.beginPath();
        ctx.arc(bx, by, 3, 0, Math.PI * 2);
        ctx.fill();
      }

      // HUD overlay
      ctx.strokeStyle = '#3b82f6';
      ctx.lineWidth = 0.5;
      ctx.strokeRect(10, 10, 300, 220);

      ctx.fillStyle = '#3b82f6';
      ctx.font = '10px monospace';
      ctx.fillText(`SRC: ${activeSource.toUpperCase()} | FRM: ${frame}`, 15, 25);

      animRef.current = requestAnimationFrame(animate);
    };
    animate();
    return () => cancelAnimationFrame(animRef.current);
  }, [isActive, activeSource]);

  const captureFrame = () => {
    const frame: CameraFrame = {
      id: `frame-${Date.now()}`,
      timestamp: new Date().toISOString(),
      source: activeSource,
      type: activeSource as 'sensor' | 'satellite' | 'drone' | 'thermal',
      confidence: 0.75 + Math.random() * 0.2,
      objects: [
        { label: 'target', bbox: [100, 80, 60, 40], confidence: 0.85 },
        { label: 'decoy', bbox: [200, 120, 30, 30], confidence: 0.62 },
      ],
    };
    setCapturedFrames(prev => [frame, ...prev].slice(0, 50));
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-700/30">
        <div className="flex items-center gap-2">
          <Camera size={16} className="text-primary-400" />
          <span className="text-sm font-semibold text-surface-200">Sensor Feed</span>
        </div>
        <div className="flex gap-1">
          {['sensor', 'satellite', 'drone', 'thermal'].map(src => (
            <button
              key={src}
              onClick={() => setActiveSource(src)}
              className={`text-[10px] px-2 py-0.5 rounded ${
                activeSource === src ? 'bg-primary-500/20 text-primary-300' : 'text-surface-500 hover:text-surface-300'
              }`}
            >
              {src}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 p-2">
        <div className="relative rounded-lg overflow-hidden bg-surface-900">
          <canvas ref={canvasRef} width={320} height={240} className="w-full" />
          <div className="absolute bottom-2 left-2 flex gap-1">
            <button
              onClick={() => setIsActive(!isActive)}
              className="p-1.5 rounded bg-black/50 hover:bg-black/70 text-white"
            >
              {isActive ? <Square size={12} /> : <Play size={12} />}
            </button>
            <button onClick={captureFrame} className="p-1.5 rounded bg-black/50 hover:bg-black/70 text-white">
              <Image size={12} />
            </button>
            <button className="p-1.5 rounded bg-black/50 hover:bg-black/70 text-white">
              <Download size={12} />
            </button>
            <button className="p-1.5 rounded bg-black/50 hover:bg-black/70 text-white">
              <Scan size={12} />
            </button>
          </div>
        </div>
        {capturedFrames.length > 0 && (
          <div className="mt-2 space-y-1 max-h-32 overflow-auto">
            {capturedFrames.slice(0, 5).map(frame => (
              <div key={frame.id} className="flex items-center gap-2 p-1.5 rounded bg-surface-800/50">
                <Video size={10} className="text-primary-400" />
                <div className="flex-1 min-w-0">
                  <div className="text-[10px] text-surface-400 truncate">{frame.source} · {frame.objects.length} objects</div>
                </div>
                <span className="text-[10px] text-surface-500">{(frame.confidence * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default CameraFeed;
