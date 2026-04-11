use crate::*;

mod linear;
pub use linear::*;

mod linmat;
pub use linmat::*;

mod affine;
pub use affine::*;

mod affmat;
pub use affmat::*;

mod poly;
pub use poly::*;

mod bij;
pub use bij::*;

mod tinv;
pub use tinv::*;

mod semitinv;
pub use semitinv::*;

mod fakelin;
pub use fakelin::*;

mod complex;
pub use complex::*;

mod divtinv;
pub use divtinv::*;

mod extend;
pub use extend::*;

pub fn all() {
    let mut handles = Vec::new();
    for s in [linear_search, linmat_search, affine_search, affmat_search, poly_search, bij_plus_search, bij_mul_search, c_search, semitinv_search, tinv_search, db_search, db_cart_search, complex_linear_search, complex_affine_search, orbit_anti255_search] {
        handles.push(std::thread::spawn(s));
    }
    for h in handles {
        h.join().unwrap();
    }
}
