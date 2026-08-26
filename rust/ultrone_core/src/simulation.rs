// Fixed-step simulation driver over a world state.

use crate::world_state::WorldState;
use pyo3::prelude::*;

#[pyclass]
pub struct Simulator {
    world: WorldState,
    dt: f64,
}

#[pymethods]
impl Simulator {
    #[new]
    fn new(world: WorldState, dt: Option<f64>) -> Self {
        Self { world, dt: dt.unwrap_or(1.0) }
    }

    /// Advance `ticks` fixed steps; returns the world tick afterwards.
    fn run(&mut self, ticks: u64) -> u64 {
        for _ in 0..ticks {
            self.world.step(self.dt);
        }
        self.world.tick()
    }

    fn world_tick(&self) -> u64 {
        self.world.tick()
    }
}