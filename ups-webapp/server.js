const express = require("express");
const bcrypt = require("bcrypt");
const session = require("express-session");
const flash = require("express-flash");
const passport = require("passport");
const initializePassport = require("./passportConfig");

initializePassport(passport);

const app = express();

const { pool } = require("./dbConfig");

const PORT = process.env.PORT || 4000;

app.set("view engine", "ejs");

app.use(express.urlencoded({ extended: false }));
app.use(
  session({
    secret: "secret",
    resave: false,
    saveUninitialized: false,
  })
);
app.use(passport.initialize());
app.use(passport.session());
app.use(flash());

app.get("/", (req, res) => {
  res.render("index");
});

app.get("/users/register", checkAuth, (req, res) => {
  res.render("register");
});

app.post("/users/register", async (req, res) => {
  let { name, email, password, passwordc, amznid } = req.body;
  console.log({ name, email, password, passwordc, amznid });

  if (!amznid) {
    amznid = null;
  }

  let errors = [];

  if (!name || !email || !password || !passwordc) {
    errors.push({ message: "Please enter all fields" });
  }

  if (password != passwordc) {
    errors.push({ message: "Passwords do not match" });
  }

  if (errors.length > 0) {
    res.render("register", { errors });
  } else {
    let hashedPassword = await bcrypt.hash(password, 10);
    console.log(hashedPassword);

    pool.query(
      `SELECT * FROM users 
      WHERE email = $1`,
      [email],
      (err, results) => {
        if (err) throw err;
        console.log(results.rows);
        if (results.rowCount > 0) {
          errors.push({ message: "Email already registered" });
          res.render("register", { errors });
        } else {
          pool.query(
            `INSERT INTO users (name, email, password, amznid) 
            VALUES ($1, $2, $3, $4) 
            RETURNING id, password`,
            [name, email, hashedPassword, amznid],
            (err, results) => {
              if (err) throw err;
              console.log(results.rows);
              req.flash("success_msg", "You are now registered. Please log in");
              res.redirect("/users/login");
            }
          );
        }
      }
    );
  }
});

app.get("/users/login", checkAuth, (req, res) => {
  res.render("login");
});

app.post(
  "/users/login",
  passport.authenticate("local", {
    successRedirect: "/users/dashboard",
    failureRedirect: "/users/login",
    failureFlash: true,
  })
);

app.get("/users/dashboard", checkNotAuth, (req, res) => {
  let packages = [];
  pool.query(
    `SELECT amznid FROM users 
    WHERE email = $1`,
    [req.user.email],
    (err, results) => {
      if (err) throw err;
      console.log(results.rows);
      if (results.rowCount > 0) {
        let { amznid } = results.rows[0];
        console.log("amznid: " + amznid);
        pool.query(
          `SELECT "packageId", "warehouseId", "truckId", status, x, y FROM package 
          WHERE "userId" = $1`,
          [amznid],
          (err, results) => {
            if (err) throw err;
            console.log(results.rows);
            for (let i = 0; i < results.rowCount; i++) {
              let { packageId, warehouseId, truckId, status, x, y } =
                results.rows[i];
              console.log({ packageId, warehouseId, truckId, status, x, y });
              packages.push({
                packageid: packageId,
                warehouseid: warehouseId,
                truckid: truckId,
                destination: `(${x}, ${y})`,
                status: status,
                items: 1,
              });
              console.log(packages);
            }
            res.render("dashboard", {
              user: req.user.name,
              packages: packages,
            });
          }
        );
      }
    }
  );
});

app.post("/users/package/track", checkNotAuth, (req, res) => {
  let { trackingnum } = req.body;
  let package;
  pool.query(
    `SELECT "warehouseId", "truckId", status, x, y FROM package 
    WHERE "packageId" = $1`,
    [trackingnum],
    (err, results) => {
      if (err) throw err;
      console.log(results.rows);
      if (results.rowCount > 0) {
        let { warehouseId, truckId, status, x, y } = results.rows[0];
        console.log({ warehouseId, truckId, status, x, y });
        package = {
          packageid: trackingnum,
          warehouseid: warehouseId,
          truckid: truckId,
          destination: `(${x}, ${y})`,
          status: status,
          items: 1,
        };
        console.log(package);
      }
      console.log("Tracking number: " + trackingnum);
      res.render("trackpackage", {
        trackingnum: trackingnum,
        package: package,
      });
    }
  );
});

app.post("/guest/package/track", (req, res) => {
  let { trackingnum } = req.body;
  let package;
  pool.query(
    `SELECT "warehouseId", "truckId", status, x, y FROM package 
    WHERE "packageId" = $1`,
    [trackingnum],
    (err, results) => {
      if (err) throw err;
      console.log(results.rows);
      if (results.rowCount > 0) {
        let { warehouseId, truckId, status, x, y } = results.rows[0];
        console.log({ warehouseId, truckId, status, x, y });
        package = {
          packageid: trackingnum,
          warehouseid: warehouseId,
          truckid: truckId,
          destination: `(${x}, ${y})`,
          status: status,
          items: 1,
        };
        console.log(package);
      }
      console.log("Tracking number: " + trackingnum);
      res.render("trackpackage", {
        guest: true,
        trackingnum: trackingnum,
        package: package,
      });
    }
  );
});

app.get("/guest/packages/:packageid", (req, res) => {
  let items = [];
  pool.query(
    `SELECT description, count FROM items
                WHERE "packageId" = $1`,
    [req.params.packageid],
    (err, results) => {
      if (err) throw err;
      console.log(results.rows);
      for (let i = 0; i < results.rowCount; i++) {
        let { description, count } = results.rows[i];
        items.push({
          description: description,
          count: count,
        });
      }
      console.log(items);
      res.render("package", {
        guest: true,
        id: req.params.packageid,
        items: items,
      });
    }
  );
});

app.get("/users/packages/:packageid", checkNotAuth, (req, res) => {
  let items = [];
  pool.query(
    `SELECT description, count FROM items
                WHERE "packageId" = $1`,
    [req.params.packageid],
    (err, results) => {
      if (err) throw err;
      console.log(results.rows);
      for (let i = 0; i < results.rowCount; i++) {
        let { description, count } = results.rows[i];
        items.push({
          description: description,
          count: count,
        });
      }
      console.log(items);
      res.render("package", {
        id: req.params.packageid,
        items: items,
      });
    }
  );
});

app.get("/users/packages/:packageid/changedest", checkNotAuth, (req, res) => {
  res.render("changedest", { id: req.params.packageid });
});

app.post("/users/packages/:packageid/changedest", checkNotAuth, (req, res) => {
  let { x, y } = req.body;
  (async () => {
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      await client.query(
        `SELECT * FROM package WHERE "packageId" = $1 FOR UPDATE`,
        [req.params.packageid]
      );
      await client.query(
        `UPDATE package SET x=$1, y=$2 WHERE "packageId" = $3`,
        [x, y, req.params.packageid]
      );
      await client.query("COMMIT");
      req.flash("success_msg", "Change of destination successful");
      res.render("changedest", { id: req.params.packageid });
    } catch (e) {
      await client.query("ROLLBACK");
      throw e;
    } finally {
      client.release();
    }
  })();
});

app.get("/users/logout", (req, res) => {
  req.logOut((err) => {
    if (err) throw err;
    req.flash("success_msg", "You have logged out");
    res.redirect("/users/login");
  });
});

function checkAuth(req, res, next) {
  if (req.isAuthenticated()) {
    return res.redirect("/users/dashboard");
  }
  next();
}

function checkNotAuth(req, res, next) {
  if (req.isAuthenticated()) {
    return next();
  }

  res.redirect("/users/login");
}

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
