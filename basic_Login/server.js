const express = require("express");
const session = require("express-session");
const path = require("path");

const app = express();
const PORT = 3000;

// Demo users (in real apps, these come from a DB + hashed passwords)
const USERS = [
  { id: 1, username: "abhay", password: "1234", role: "admin" },
  { id: 2, username: "user1", password: "1111", role: "user" },
  { id: 3, username: "user2", password: "2222", role: "user" }
];

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use(
  session({
    secret: "replace-this-with-a-strong-secret",
    resave: false,
    saveUninitialized: false
  })
);

// Serve static pages
app.use("/public", express.static(path.join(__dirname, "public")));

// Helper middleware: must be logged in
function requireAuth(req, res, next) {
  if (!req.session.user) return res.status(401).send("Not logged in");
  next();
}

// Home -> redirect
app.get("/", (req, res) => {
  if (req.session.user) return res.redirect("/dashboard");
  return res.redirect("/login");
});

// Login page
app.get("/login", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "login.html"));
});

// Dashboard page (protected)
app.get("/dashboard", requireAuth, (req, res) => {
  res.sendFile(path.join(__dirname, "public", "dashboard.html"));
});

// Login API
app.post("/api/login", (req, res) => {
  const { username, password } = req.body;

  const user = USERS.find(
    (u) => u.username === username && u.password === password
  );

  if (!user) return res.status(401).json({ ok: false, message: "Invalid login" });

  // Store in session (never store password)
  req.session.user = { id: user.id, username: user.username, role: user.role };
  return res.json({ ok: true, user: req.session.user });
});

// Logout API
app.post("/api/logout", (req, res) => {
  req.session.destroy(() => {
    res.json({ ok: true });
  });
});

// Current user API
app.get("/api/me", (req, res) => {
  res.json({ user: req.session.user || null });
});

/**
 * Switch user API:
 * - If you are logged in, you can switch to another username without typing password.
 * - Typical use: admin testing accounts.
 * - You can restrict it to admins only (recommended). I’ve already done that.
 */
app.post("/api/switch-user", requireAuth, (req, res) => {
  const { username } = req.body;

  if (req.session.user.role !== "admin") {
    return res.status(403).json({ ok: false, message: "Only admin can switch users" });
  }

  const user = USERS.find((u) => u.username === username);
  if (!user) return res.status(404).json({ ok: false, message: "User not found" });

  req.session.user = { id: user.id, username: user.username, role: user.role };
  return res.json({ ok: true, user: req.session.user });
});

app.listen(PORT, () => {
  console.log(`Running: http://localhost:${PORT}`);
  console.log(`Login:   http://localhost:${PORT}/login`);
});
