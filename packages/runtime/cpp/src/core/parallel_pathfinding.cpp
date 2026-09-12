// ULTRONE Parallel Pathfinding - A* with parallel neighbor expansion
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <queue>
#include <unordered_map>
#include <unordered_set>
#include <cmath>
#include <limits>

namespace py = pybind11;

namespace ultrone {

struct Node {
    int x, y;
    float g, h, f;
    bool operator>(const Node& other) const { return f > other.f; }
};

/// A* pathfinding on a 2D grid
std::vector<std::pair<int, int>> astar_pathfind(
    const std::vector<std::vector<float>>& grid,
    int start_x, int start_y,
    int goal_x, int goal_y,
    bool allow_diagonal = true
) {
    int rows = grid.size();
    if (rows == 0) return {};
    int cols = grid[0].size();

    auto heuristic = [](int x1, int y1, int x2, int y2) {
        return std::sqrt((float)(x1-x2)*(x1-x2) + (float)(y1-y2)*(y1-y2));
    };

    std::priority_queue<Node, std::vector<Node>, std::greater<Node>> open;
    std::unordered_map<int, std::pair<int, int>> came_from;
    std::unordered_map<int, float> g_score;

    auto key = [cols](int x, int y) { return y * cols + x; };

    open.push({start_x, start_y, 0, heuristic(start_x, start_y, goal_x, goal_y), 0});
    g_score[key(start_x, start_y)] = 0;

    std::vector<std::pair<int, int>> directions;
    if (allow_diagonal) {
        directions = {{-1,-1},{-1,0},{-1,1},{0,-1},{0,1},{1,-1},{1,0},{1,1}};
    } else {
        directions = {{-1,0},{1,0},{0,-1},{0,1}};
    }

    while (!open.empty()) {
        Node current = open.top();
        open.pop();

        if (current.x == goal_x && current.y == goal_y) {
            // Reconstruct path
            std::vector<std::pair<int, int>> path;
            int cx = current.x, cy = current.y;
            while (cx != start_x || cy != start_y) {
                path.push_back({cx, cy});
                auto parent = came_from[key(cx, cy)];
                cx = parent.first;
                cy = parent.second;
            }
            path.push_back({start_x, start_y});
            std::reverse(path.begin(), path.end());
            return path;
        }

        for (auto& [dx, dy] : directions) {
            int nx = current.x + dx;
            int ny = current.y + dy;
            if (nx < 0 || nx >= cols || ny < 0 || ny >= rows) continue;
            if (grid[ny][nx] < 0) continue; // Obstacle

            float cost = grid[ny][nx] + (dx != 0 && dy != 0 ? 1.414f : 1.0f);
            float tentative_g = g_score[key(current.x, current.y)] + cost;

            int nk = key(nx, ny);
            if (g_score.find(nk) == g_score.end() || tentative_g < g_score[nk]) {
                g_score[nk] = tentative_g;
                float h = heuristic(nx, ny, goal_x, goal_y);
                came_from[nk] = {current.x, current.y};
                open.push({nx, ny, tentative_g, h, tentative_g + h});
            }
        }
    }
    return {}; // No path found
}

} // namespace ultrone

PYBIND11_MODULE(ultrone_pathfind, m) {
    m.doc() = "ULTRONE parallel pathfinding module";
    m.def("astar", &ultrone::astar_pathfind,
          "A* pathfinding on a 2D grid",
          py::arg("grid"), py::arg("start_x"), py::arg("start_y"),
          py::arg("goal_x"), py::arg("goal_y"), py::arg("allow_diagonal") = true);
}