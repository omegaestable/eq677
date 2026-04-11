use crate::*;

pub type Group = Vec<Perm>;
pub type Perm = Vec<usize>;

#[cfg(not(windows))]
use nauty_pet::autom::{AutomGroup, AutomStats, TryIntoAutomGroupNautyDense, TryIntoAutomStatsTraces};
#[cfg(not(windows))]
use nauty_pet::canon::*;
#[cfg(not(windows))]
use nauty_pet::prelude::*;
#[cfg(not(windows))]
use petgraph::visit::EdgeRef;
#[cfg(not(windows))]
use std::collections::{HashMap, HashSet};

#[cfg(not(windows))]
type Graph = petgraph::graph::UnGraph<NodeType, EdgeType>;

#[cfg(not(windows))]
#[derive(Eq, Hash, Ord, PartialEq, PartialOrd)]
enum NodeType {
    Elem, XYZ
}

#[cfg(not(windows))]
#[derive(Eq, Hash, Ord, PartialEq, PartialOrd)]
enum EdgeType {
    X, Y, Z
}

#[cfg(windows)]
pub struct AutomStats;

#[cfg(windows)]
impl AutomStats {
    pub fn grpsize(&self) -> f64 {
        1.0
    }
}

impl MatrixMagma {
    #[cfg(not(windows))]
    pub fn canonicalize2(&self) -> MatrixMagma {
        let g = graphify(self);
        let g = g.into_canon_traces();
        de_graphify(&g)
    }

    #[cfg(windows)]
    pub fn canonicalize2(&self) -> MatrixMagma {
        self.clone()
    }

    #[cfg(not(windows))]
    pub fn autom_stats(&self) -> AutomStats {
        graphify(self).try_into_autom_stats_traces().unwrap()
    }

    #[cfg(windows)]
    pub fn autom_stats(&self) -> AutomStats {
        AutomStats
    }

    #[cfg(not(windows))]
    pub fn autom_group(&self) -> Group {
        let mut a = graphify(self).try_into_autom_group_nauty_dense().unwrap().0;
        for x in &mut a {
            x.truncate(self.n);
        }
        a
    }

    #[cfg(windows)]
    pub fn autom_group(&self) -> Group {
        vec![(0..self.n).collect()]
    }

    pub fn autom_group_mini(&self) -> Group {
        minimize_gap(self.autom_group())
    }
}

pub fn orbits(autom: &[Vec<usize>]) -> Vec<usize> {
    let n = autom[0].len();
    let mut orbits: Vec<usize> = (0..n).collect();
    for aut in autom {
        for i in 0..n {
            let j = aut[i];
            if j < orbits[i] {
                orbits[i] = j;
            }
        }
    }
    orbits
}

#[cfg(not(windows))]
fn graphify(m: &MatrixMagma) -> Graph {
    let mut g = Graph::new_undirected();
    let mut nodes = Vec::new();
    for x in 0..m.n {
        nodes.push(g.add_node(NodeType::Elem));
    }
    for x in 0..m.n {
        for y in 0..m.n {
            let z = m.f(x, y);
            if z != usize::MAX {
                let xyz = g.add_node(NodeType::XYZ);
                g.add_edge(xyz, nodes[x], EdgeType::X);
                g.add_edge(xyz, nodes[y], EdgeType::Y);
                g.add_edge(xyz, nodes[z], EdgeType::Z);
            }
        }
    }
    g
}

#[cfg(not(windows))]
fn de_graphify(g: &Graph) -> MatrixMagma {
    let mut nodes = HashMap::new();
    for idx in g.node_indices() {
        if g[idx] == NodeType::Elem {
            nodes.insert(idx, nodes.len());
        }
    }

    let mut m = MatrixMagma::undefined(nodes.len());

    for idx in g.node_indices() {
        if g[idx] == NodeType::XYZ {
            let mut x = None;
            let mut y = None;
            let mut z = None;
            for e in g.edges(idx) {
                match e.weight() {
                    EdgeType::X => { x = Some(e.target()); }
                    EdgeType::Y => { y = Some(e.target()); }
                    EdgeType::Z => { z = Some(e.target()); }
                }
            }
            let (x, y, z) = (x.unwrap(), y.unwrap(), z.unwrap());
            m.set_f(nodes[&x], nodes[&y], nodes[&z]);
        }
    }

    m
}
