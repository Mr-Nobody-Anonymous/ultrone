// ULTRONE Cluster Manager — Go implementation
// Handles cluster management, distributed workers, scheduling,
// load balancing, and service discovery.

package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"
)

// Worker represents a distributed worker node
type Worker struct {
	ID        string    `json:"worker_id"`
	Address   string    `json:"address"`
	Status    string    `json:"status"`
	CPU       float64   `json:"cpu_usage"`
	Memory    float64   `json:"memory_usage"`
	LastSeen  time.Time `json:"last_seen"`
	TasksRun  int       `json:"tasks_run"`
}

// Task represents a scheduled task
type Task struct {
	ID        string                 `json:"task_id"`
	Type      string                 `json:"type"`
	Payload   map[string]interface{} `json:"payload"`
	Status    string                 `json:"status"`
	WorkerID  string                 `json:"worker_id"`
	CreatedAt time.Time              `json:"created_at"`
}

// ClusterManager manages the ULTRONE distributed cluster
type ClusterManager struct {
	mu       sync.RWMutex
	workers  map[string]*Worker
	tasks    map[string]*Task
	scheduler *Scheduler
}

// Scheduler handles task scheduling and load balancing
type Scheduler struct {
	strategy string
}

// NewClusterManager creates a new cluster manager
func NewClusterManager() *ClusterManager {
	return &ClusterManager{
		workers:  make(map[string]*Worker),
		tasks:    make(map[string]*Task),
		scheduler: &Scheduler{strategy: "least-loaded"},
	}
}

// RegisterWorker registers a new worker node
func (cm *ClusterManager) RegisterWorker(id, address string) *Worker {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	worker := &Worker{
		ID:       id,
		Address:  address,
		Status:   "active",
		LastSeen: time.Now(),
	}
	cm.workers[id] = worker
	log.Printf("Worker registered: %s at %s", id, address)
	return worker
}

// UnregisterWorker removes a worker from the cluster
func (cm *ClusterManager) UnregisterWorker(id string) {
	cm.mu.Lock()
	defer cm.mu.Unlock()
	delete(cm.workers, id)
	log.Printf("Worker unregistered: %s", id)
}

// Heartbeat updates worker status
func (cm *ClusterManager) Heartbeat(id string, cpu, memory float64) error {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	worker, exists := cm.workers[id]
	if !exists {
		return fmt.Errorf("worker %s not found", id)
	}
	worker.CPU = cpu
	worker.Memory = memory
	worker.LastSeen = time.Now()
	worker.Status = "active"
	return nil
}

// SubmitTask submits a new task for scheduling
func (cm *ClusterManager) SubmitTask(taskType string, payload map[string]interface{}) *Task {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	task := &Task{
		ID:        fmt.Sprintf("TASK-%d", time.Now().UnixNano()),
		Type:      taskType,
		Payload:   payload,
		Status:    "pending",
		CreatedAt: time.Now(),
	}
	cm.tasks[task.ID] = task

	// Schedule to least-loaded worker
	cm.scheduleTask(task)
	return task
}

// scheduleTask assigns a task to the best available worker
func (cm *ClusterManager) scheduleTask(task *Task) {
	var bestWorker *Worker
	minLoad := 1.0

	for _, worker := range cm.workers {
		if worker.Status != "active" {
			continue
		}
		load := (worker.CPU + worker.Memory) / 2
		if load < minLoad {
			minLoad = load
			bestWorker = worker
		}
	}

	if bestWorker != nil {
		task.WorkerID = bestWorker.ID
		task.Status = "assigned"
		bestWorker.TasksRun++
		log.Printf("Task %s assigned to worker %s", task.ID, bestWorker.ID)
	}
}

// GetWorkers returns all registered workers
func (cm *ClusterManager) GetWorkers() []*Worker {
	cm.mu.RLock()
	defer cm.mu.RUnlock()
	workers := make([]*Worker, 0, len(cm.workers))
	for _, w := range cm.workers {
		workers = append(workers, w)
	}
	return workers
}

// GetStats returns cluster statistics
func (cm *ClusterManager) GetStats() map[string]interface{} {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	activeWorkers := 0
	for _, w := range cm.workers {
		if w.Status == "active" {
			activeWorkers++
		}
	}

	return map[string]interface{}{
		"type":           "ClusterManager",
		"total_workers":  len(cm.workers),
		"active_workers": activeWorkers,
		"total_tasks":    len(cm.tasks),
		"scheduler":      cm.scheduler.strategy,
	}
}

// StartHTTPServer starts the cluster manager HTTP API
func (cm *ClusterManager) StartHTTPServer(port int) error {
	mux := http.NewServeMux()

	mux.HandleFunc("/workers", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(cm.GetWorkers())
	})

	mux.HandleFunc("/stats", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(cm.GetStats())
	})

	mux.HandleFunc("/register", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		var req struct {
			ID      string `json:"worker_id"`
			Address string `json:"address"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		worker := cm.RegisterWorker(req.ID, req.Address)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(worker)
	})

	mux.HandleFunc("/submit", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		var req struct {
			Type    string                 `json:"type"`
			Payload map[string]interface{} `json:"payload"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		task := cm.SubmitTask(req.Type, req.Payload)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(task)
	})

	addr := fmt.Sprintf(":%d", port)
	log.Printf("ULTRONE Cluster Manager starting on %s", addr)
	return http.ListenAndServe(addr, mux)
}

func main() {
	cm := NewClusterManager()
	log.Fatal(cm.StartHTTPServer(9091))
}