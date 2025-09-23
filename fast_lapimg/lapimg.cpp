#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <memory>
#include <new>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
  int width;
  int height;
  uint8_t *data; // RGB, row-major, width*height*3
} ImageRGB;

static void blend_rect(ImageRGB *img, int x1, int y1, int x2, int y2, uint8_t r,
                       uint8_t g, uint8_t b, uint8_t a) {
  if (!img || !img->data)
    return;
  if (x1 > x2) {
    int t = x1;
    x1 = x2;
    x2 = t;
  }
  if (y1 > y2) {
    int t = y1;
    y1 = y2;
    y2 = t;
  }
  if (x1 < 0)
    x1 = 0;
  if (y1 < 0)
    y1 = 0;
  if (x2 >= img->width)
    x2 = img->width - 1;
  if (y2 >= img->height)
    y2 = img->height - 1;
  float af = a / 255.0f;
  float ia = 1.0f - af;
  for (int y = y1; y <= y2; ++y) {
    uint8_t *row = img->data + (size_t)y * img->width * 3;
    for (int x = x1; x <= x2; ++x) {
      uint8_t *p = row + (size_t)x * 3;
      p[0] = (uint8_t)((float)r * af + (float)p[0] * ia);
      p[1] = (uint8_t)((float)g * af + (float)p[1] * ia);
      p[2] = (uint8_t)((float)b * af + (float)p[2] * ia);
    }
  }
}

// Minimal 8x8 bitmap font for numbers, colon, dot, letters used
typedef struct {
  char ch;
  uint8_t rows[8];
} Glyph;

static const Glyph FONT[] = {
    {'0', {0x3E, 0x41, 0x43, 0x45, 0x49, 0x51, 0x41, 0x3E}},
    {'1', {0x08, 0x18, 0x08, 0x08, 0x08, 0x08, 0x08, 0x3E}},
    {'2', {0x3E, 0x41, 0x01, 0x1E, 0x20, 0x40, 0x40, 0x7F}},
    {'3', {0x3E, 0x41, 0x01, 0x1E, 0x01, 0x01, 0x41, 0x3E}},
    {'4', {0x41, 0x41, 0x41, 0x7F, 0x01, 0x01, 0x01, 0x01}},
    {'5', {0x7F, 0x40, 0x40, 0x7E, 0x01, 0x01, 0x41, 0x3E}},
    {'6', {0x3E, 0x41, 0x40, 0x7E, 0x41, 0x41, 0x41, 0x3E}},
    {'7', {0x7F, 0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20}},
    {'8', {0x3E, 0x41, 0x41, 0x3E, 0x41, 0x41, 0x41, 0x3E}},
    {'9', {0x3E, 0x41, 0x41, 0x41, 0x3F, 0x01, 0x41, 0x3E}},
    {':', {0x00, 0x00, 0x18, 0x18, 0x00, 0x18, 0x18, 0x00}},
    {'.', {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x18, 0x18}},
    {' ', {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},
    {'A', {0x3E, 0x41, 0x41, 0x41, 0x7F, 0x41, 0x41, 0x41}},
    {'B', {0x7C, 0x42, 0x42, 0x7C, 0x42, 0x42, 0x42, 0x7C}},
    {'C', {0x3E, 0x41, 0x40, 0x40, 0x40, 0x40, 0x41, 0x3E}},
    {'D', {0x7C, 0x42, 0x41, 0x41, 0x41, 0x41, 0x42, 0x7C}},
    {'E', {0x7F, 0x40, 0x40, 0x7E, 0x40, 0x40, 0x40, 0x7F}},
    {'F', {0x7F, 0x40, 0x40, 0x7E, 0x40, 0x40, 0x40, 0x40}},
    {'G', {0x3E, 0x41, 0x40, 0x47, 0x41, 0x41, 0x41, 0x3E}},
    {'H', {0x41, 0x41, 0x41, 0x7F, 0x41, 0x41, 0x41, 0x41}},
    {'I', {0x3E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x08, 0x3E}},
    {'J', {0x1F, 0x01, 0x01, 0x01, 0x01, 0x41, 0x41, 0x3E}},
    {'K', {0x41, 0x42, 0x44, 0x58, 0x64, 0x42, 0x41, 0x41}},
    {'L', {0x40, 0x40, 0x40, 0x40, 0x40, 0x40, 0x40, 0x7F}},
    {'M', {0x41, 0x63, 0x55, 0x49, 0x41, 0x41, 0x41, 0x41}},
    {'N', {0x41, 0x61, 0x51, 0x49, 0x45, 0x43, 0x41, 0x41}},
    {'O', {0x3E, 0x41, 0x41, 0x41, 0x41, 0x41, 0x41, 0x3E}},
    {'P', {0x7C, 0x42, 0x42, 0x7C, 0x40, 0x40, 0x40, 0x40}},
    {'Q', {0x3E, 0x41, 0x41, 0x41, 0x45, 0x42, 0x3D, 0x01}},
    {'R', {0x7C, 0x42, 0x42, 0x7C, 0x48, 0x44, 0x42, 0x41}},
    {'S', {0x3E, 0x41, 0x40, 0x3E, 0x01, 0x01, 0x41, 0x3E}},
    {'T', {0x7F, 0x08, 0x08, 0x08, 0x08, 0x08, 0x08, 0x08}},
    {'U', {0x41, 0x41, 0x41, 0x41, 0x41, 0x41, 0x41, 0x3E}},
    {'V', {0x41, 0x41, 0x41, 0x41, 0x41, 0x22, 0x14, 0x08}},
    {'W', {0x41, 0x41, 0x41, 0x41, 0x49, 0x55, 0x63, 0x41}},
    {'X', {0x41, 0x22, 0x14, 0x08, 0x14, 0x22, 0x41, 0x41}},
    {'Y', {0x41, 0x22, 0x14, 0x08, 0x08, 0x08, 0x08, 0x08}},
    {'Z', {0x7F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x7F}},
    // Lowercase letters
    {'a', {0x00, 0x00, 0x3E, 0x02, 0x3E, 0x42, 0x3E, 0x00}},
    {'b', {0x40, 0x40, 0x7C, 0x42, 0x42, 0x42, 0x7C, 0x00}},
    {'c', {0x00, 0x00, 0x3E, 0x42, 0x40, 0x42, 0x3E, 0x00}},
    {'d', {0x02, 0x02, 0x3E, 0x42, 0x42, 0x42, 0x3E, 0x00}},
    {'e', {0x00, 0x00, 0x3E, 0x42, 0x7E, 0x40, 0x3E, 0x00}},
    {'f', {0x1E, 0x22, 0x20, 0x7C, 0x20, 0x20, 0x20, 0x00}},
    {'g', {0x00, 0x00, 0x3E, 0x42, 0x3E, 0x02, 0x3C, 0x00}},
    {'h', {0x40, 0x40, 0x7C, 0x42, 0x42, 0x42, 0x42, 0x00}},
    {'i', {0x10, 0x00, 0x30, 0x10, 0x10, 0x10, 0x38, 0x00}},
    {'j', {0x04, 0x00, 0x0C, 0x04, 0x04, 0x84, 0x78, 0x00}},
    {'k', {0x40, 0x40, 0x44, 0x48, 0x70, 0x48, 0x44, 0x00}},
    {'l', {0x30, 0x10, 0x10, 0x10, 0x10, 0x10, 0x38, 0x00}},
    {'m', {0x00, 0x00, 0x6A, 0x55, 0x55, 0x55, 0x55, 0x00}},
    {'n', {0x00, 0x00, 0x7C, 0x42, 0x42, 0x42, 0x42, 0x00}},
    {'o', {0x00, 0x00, 0x3C, 0x42, 0x42, 0x42, 0x3C, 0x00}},
    {'p', {0x00, 0x00, 0x7C, 0x42, 0x7C, 0x40, 0x40, 0x00}},
    {'q', {0x00, 0x00, 0x3E, 0x42, 0x3E, 0x02, 0x02, 0x00}},
    {'r', {0x00, 0x00, 0x5E, 0x60, 0x40, 0x40, 0x40, 0x00}},
    {'s', {0x00, 0x00, 0x3E, 0x40, 0x3C, 0x02, 0x3C, 0x00}},
    {'t', {0x10, 0x10, 0x3E, 0x10, 0x10, 0x12, 0x0C, 0x00}},
    {'u', {0x00, 0x00, 0x42, 0x42, 0x42, 0x46, 0x3A, 0x00}},
    {'v', {0x00, 0x00, 0x42, 0x42, 0x42, 0x24, 0x18, 0x00}},
    {'w', {0x00, 0x00, 0x42, 0x49, 0x55, 0x63, 0x41, 0x00}},
    {'x', {0x00, 0x00, 0x42, 0x24, 0x18, 0x24, 0x42, 0x00}},
    {'y', {0x00, 0x00, 0x42, 0x42, 0x3E, 0x02, 0x3C, 0x00}},
    {'z', {0x00, 0x00, 0x7E, 0x04, 0x18, 0x20, 0x7E, 0x00}},
};

static const Glyph *find_glyph(char c) {
  for (size_t i = 0; i < sizeof(FONT) / sizeof(FONT[0]); ++i)
    if (FONT[i].ch == c)
      return &FONT[i];
  return NULL;
}

static void draw_text(ImageRGB *img, int x, int y, const char *text, uint8_t r,
                      uint8_t g, uint8_t b, int scale) {
  if (!img || !img->data || !text)
    return;
  if (scale < 1)
    scale = 1;
  int cursor = x;
  int pixel_scale = scale * 3;
  int char_advance = 9 * pixel_scale; // match Python spacing (9 * scale * 3)
  while (*text) {
    const Glyph *gph = find_glyph(*text);
    if (gph) {
      for (int row = 0; row < 8; ++row) {
        uint8_t bits = gph->rows[row];
        for (int col = 0; col < 8; ++col) {
          if (bits & (1u << (7 - col))) {
            for (int sy = 0; sy < pixel_scale; ++sy) {
              int py = y + row * pixel_scale + sy;
              if (py < 0 || py >= img->height)
                continue;
              uint8_t *rowp = img->data + (size_t)py * img->width * 3;
              for (int sx = 0; sx < pixel_scale; ++sx) {
                int px = cursor + col * pixel_scale + sx;
                if (px < 0 || px >= img->width)
                  continue;
                uint8_t *p = rowp + (size_t)px * 3;
                p[0] = r;
                p[1] = g;
                p[2] = b;
              }
            }
          }
        }
      }
    }
    cursor += char_advance;
    ++text;
  }
}

static PyObject *py_compose_lap_image(PyObject *self, PyObject *args,
                                      PyObject *kwargs) {
  static const char *kwlist[] = {"width", "height", "bg_rgb", "texts", NULL};
  int width, height;
  PyObject *bg_rgb = NULL; // (r,g,b)
  PyObject *texts =
      NULL; // list of tuples: (x,y,text,(r,g,b),scale,pad,bg_rgba)
  if (!PyArg_ParseTupleAndKeywords(args, kwargs, "iiOO", (char **)kwlist,
                                   &width, &height, &bg_rgb, &texts))
    return NULL;
  int r = 30, g = 30, b = 30;
  if (PyTuple_Check(bg_rgb) && PyTuple_Size(bg_rgb) >= 3) {
    r = (int)PyLong_AsLong(PyTuple_GetItem(bg_rgb, 0));
    g = (int)PyLong_AsLong(PyTuple_GetItem(bg_rgb, 1));
    b = (int)PyLong_AsLong(PyTuple_GetItem(bg_rgb, 2));
  }
  ImageRGB img;
  img.width = width;
  img.height = height;
  img.data = (uint8_t *)malloc((size_t)width * height * 3);
  if (!img.data)
    return PyErr_NoMemory();
  for (int y = 0; y < height; ++y) {
    uint8_t *row = img.data + (size_t)y * width * 3;
    for (int x = 0; x < width; ++x) {
      row[x * 3 + 0] = (uint8_t)r;
      row[x * 3 + 1] = (uint8_t)g;
      row[x * 3 + 2] = (uint8_t)b;
    }
  }
  if (PyList_Check(texts)) {
    Py_ssize_t n = PyList_Size(texts);
    for (Py_ssize_t i = 0; i < n; ++i) {
      PyObject *item = PyList_GetItem(texts, i);
      if (!PyTuple_Check(item) || PyTuple_Size(item) < 4)
        continue;
      int x = (int)PyLong_AsLong(PyTuple_GetItem(item, 0));
      int y = (int)PyLong_AsLong(PyTuple_GetItem(item, 1));
      PyObject *pytext = PyTuple_GetItem(item, 2);
      const char *ctext =
          PyUnicode_Check(pytext) ? PyUnicode_AsUTF8(pytext) : NULL;
      PyObject *col = PyTuple_GetItem(item, 3);
      int tr = 255, tg = 255, tb = 255;
      if (PyTuple_Check(col) && PyTuple_Size(col) >= 3) {
        tr = (int)PyLong_AsLong(PyTuple_GetItem(col, 0));
        tg = (int)PyLong_AsLong(PyTuple_GetItem(col, 1));
        tb = (int)PyLong_AsLong(PyTuple_GetItem(col, 2));
      }
      int scale = 1;
      if (PyTuple_Size(item) >= 5)
        scale = (int)PyLong_AsLong(PyTuple_GetItem(item, 4));
      if (scale < 1)
        scale = 1;
      int pad = 5;
      if (PyTuple_Size(item) >= 6)
        pad = (int)PyLong_AsLong(PyTuple_GetItem(item, 5));
      PyObject *bg = NULL;
      if (PyTuple_Size(item) >= 7)
        bg = PyTuple_GetItem(item, 6);
      int br = 0, bgG = 0, bb = 0, ba = 0;
      if (bg && PyTuple_Check(bg) && PyTuple_Size(bg) >= 4) {
        br = (int)PyLong_AsLong(PyTuple_GetItem(bg, 0));
        bgG = (int)PyLong_AsLong(PyTuple_GetItem(bg, 1));
        bb = (int)PyLong_AsLong(PyTuple_GetItem(bg, 2));
        ba = (int)PyLong_AsLong(PyTuple_GetItem(bg, 3));
      }
      int char_spacing = (9 * scale * 3);
      int font_h = (8 * scale * 3);
      int text_w = (ctext ? (int)strlen(ctext) : 0) * char_spacing;
      if (ba > 0)
        blend_rect(&img, x - pad, y - pad, x + text_w + pad, y + font_h + pad,
                   (uint8_t)br, (uint8_t)bgG, (uint8_t)bb, (uint8_t)ba);
      if (ctext)
        draw_text(&img, x, y, ctext, (uint8_t)tr, (uint8_t)tg, (uint8_t)tb,
                  scale);
    }
  }
  PyObject *out = PyBytes_FromStringAndSize((const char *)img.data,
                                            (Py_ssize_t)width * height * 3);
  free(img.data);
  return out;
}

// Draw overlay onto an existing RGB buffer (bytes, width, height, texts)
static PyObject *py_draw_overlay_on_rgb(PyObject *self, PyObject *args) {
  PyObject *rgb_bytes = NULL;
  int width = 0, height = 0;
  PyObject *texts = NULL;
  if (!PyArg_ParseTuple(args, "OiiO", &rgb_bytes, &width, &height, &texts))
    return NULL;
  if (!PyBytes_Check(rgb_bytes)) {
    PyErr_SetString(PyExc_TypeError, "First arg must be bytes (RGB buffer)");
    return NULL;
  }
  Py_ssize_t in_size = PyBytes_GET_SIZE(rgb_bytes);
  if (in_size != (Py_ssize_t)width * height * 3) {
    PyErr_SetString(PyExc_ValueError,
                    "RGB buffer size does not match width*height*3");
    return NULL;
  }
  // Copy to mutable buffer
  PyObject *out =
      PyBytes_FromStringAndSize(PyBytes_AS_STRING(rgb_bytes), in_size);
  if (!out)
    return NULL;
  ImageRGB img;
  img.width = width;
  img.height = height;
  img.data = (uint8_t *)PyBytes_AS_STRING(out);
  if (PyList_Check(texts)) {
    Py_ssize_t n = PyList_Size(texts);
    for (Py_ssize_t i = 0; i < n; ++i) {
      PyObject *item = PyList_GetItem(texts, i);
      if (!PyTuple_Check(item) || PyTuple_Size(item) < 4)
        continue;
      int x = (int)PyLong_AsLong(PyTuple_GetItem(item, 0));
      int y = (int)PyLong_AsLong(PyTuple_GetItem(item, 1));
      PyObject *pytext = PyTuple_GetItem(item, 2);
      const char *ctext =
          PyUnicode_Check(pytext) ? PyUnicode_AsUTF8(pytext) : NULL;
      PyObject *col = PyTuple_GetItem(item, 3);
      int tr = 255, tg = 255, tb = 255;
      if (PyTuple_Check(col) && PyTuple_Size(col) >= 3) {
        tr = (int)PyLong_AsLong(PyTuple_GetItem(col, 0));
        tg = (int)PyLong_AsLong(PyTuple_GetItem(col, 1));
        tb = (int)PyLong_AsLong(PyTuple_GetItem(col, 2));
      }
      int scale = 1;
      if (PyTuple_Size(item) >= 5)
        scale = (int)PyLong_AsLong(PyTuple_GetItem(item, 4));
      if (scale < 1)
        scale = 1;
      int pad = 5;
      if (PyTuple_Size(item) >= 6)
        pad = (int)PyLong_AsLong(PyTuple_GetItem(item, 5));
      PyObject *bg = NULL;
      if (PyTuple_Size(item) >= 7)
        bg = PyTuple_GetItem(item, 6);
      int br = 0, bgG = 0, bb = 0, ba = 0;
      if (bg && PyTuple_Check(bg) && PyTuple_Size(bg) >= 4) {
        br = (int)PyLong_AsLong(PyTuple_GetItem(bg, 0));
        bgG = (int)PyLong_AsLong(PyTuple_GetItem(bg, 1));
        bb = (int)PyLong_AsLong(PyTuple_GetItem(bg, 2));
        ba = (int)PyLong_AsLong(PyTuple_GetItem(bg, 3));
      }
      int char_spacing = (9 * scale * 3); // keep for background width calc
      int font_h = (8 * scale * 3);
      int text_w = (ctext ? (int)strlen(ctext) : 0) * char_spacing;
      if (ba > 0)
        blend_rect(&img, x - pad, y - pad, x + text_w + pad, y + font_h + pad,
                   (uint8_t)br, (uint8_t)bgG, (uint8_t)bb, (uint8_t)ba);
      if (ctext)
        draw_text(&img, x, y, ctext, (uint8_t)tr, (uint8_t)tg, (uint8_t)tb,
                  scale);
    }
  }
  return out;
}

// Forward declare Windows-specific functions for inclusion in method table
#ifdef _WIN32
static PyObject *py_load_image_rgb(PyObject *self, PyObject *args);
static PyObject *py_save_png(PyObject *self, PyObject *args);
static PyObject *py_resize_image_rgb(PyObject *self, PyObject *args);
#endif

static PyMethodDef Methods[] = {
    {"compose_lap_image", (PyCFunction)py_compose_lap_image,
     METH_VARARGS | METH_KEYWORDS,
     (char *)"Compose RGB image buffer with text and backgrounds"},
    {"draw_overlay_on_rgb", (PyCFunction)py_draw_overlay_on_rgb, METH_VARARGS,
     (char *)"Draw overlay texts onto an existing RGB buffer and return new "
             "bytes"},
#ifdef _WIN32
    {"load_image_rgb", (PyCFunction)py_load_image_rgb, METH_VARARGS,
     (char *)"Load image via GDI+ and return (bytes,width,height) in RGB"},
    {"save_png", (PyCFunction)py_save_png, METH_VARARGS,
     (char *)"Save RGB buffer to PNG file path using a fast encoder"},
    {"resize_image_rgb", (PyCFunction)py_resize_image_rgb, METH_VARARGS,
     (char *)"Resize RGB image data using nearest neighbor interpolation"},
#endif
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT, "lapimg", "Fast lap image composition", -1, Methods};

extern "C" PyMODINIT_FUNC PyInit_lapimg(void) {
  PyObject *m = PyModule_Create(&moduledef);
  if (!m)
    return NULL;
  return m;
}

#ifdef _WIN32
#include <windows.h>
#include <wchar.h>
#include <gdiplus.h>
using namespace Gdiplus;

static int utf8_to_wide(const char *utf8, wchar_t **out_w) {
  if (!utf8)
    return 0;
  int needed = MultiByteToWideChar(CP_UTF8, 0, utf8, -1, NULL, 0);
  if (needed <= 0)
    return 0;
  wchar_t *w = (wchar_t *)malloc((size_t)needed * sizeof(wchar_t));
  if (!w)
    return 0;
  if (!MultiByteToWideChar(CP_UTF8, 0, utf8, -1, w, needed)) {
    free(w);
    return 0;
  }
  *out_w = w;
  return 1;
}

static PyObject *py_load_image_rgb(PyObject *self, PyObject *args) {
  const char *path = NULL;
  if (!PyArg_ParseTuple(args, "s", &path))
    return NULL;
  PyObject *result = NULL;
  ULONG_PTR token = 0;
  GdiplusStartupInput gdiplusStartupInput;
  if (GdiplusStartup(&token, &gdiplusStartupInput, NULL) != Ok) {
    PyErr_SetString(PyExc_RuntimeError, "GDI+ startup failed");
    return NULL;
  }
  wchar_t *wpath = NULL;
  if (!utf8_to_wide(path, &wpath)) {
    GdiplusShutdown(token);
    PyErr_SetString(PyExc_ValueError, "Path conversion failed");
    return NULL;
  }
  Bitmap *bmp = new Bitmap(wpath);
  free(wpath);
  if (!bmp || bmp->GetLastStatus() != Ok) {
    if (bmp)
      delete bmp;
    GdiplusShutdown(token);
    PyErr_SetString(PyExc_IOError, "Failed to load image via GDI+");
    return NULL;
  }
  UINT w = bmp->GetWidth();
  UINT h = bmp->GetHeight();
  Rect rect(0, 0, (INT)w, (INT)h);
  BitmapData data;
  if (bmp->LockBits(&rect, ImageLockModeRead, PixelFormat24bppRGB, &data) ==
      Ok) {
    // 24bpp BGR; convert to RGB
    size_t out_size = (size_t)w * h * 3;
    PyObject *bytes = PyBytes_FromStringAndSize(NULL, (Py_ssize_t)out_size);
    if (bytes) {
      uint8_t *dst = (uint8_t *)PyBytes_AS_STRING(bytes);
      for (UINT y = 0; y < h; ++y) {
        uint8_t *src = (uint8_t *)data.Scan0 + y * (size_t)data.Stride;
        for (UINT x = 0; x < w; ++x) {
          dst[(y * (size_t)w + x) * 3 + 0] = src[x * 3 + 2];
          dst[(y * (size_t)w + x) * 3 + 1] = src[x * 3 + 1];
          dst[(y * (size_t)w + x) * 3 + 2] = src[x * 3 + 0];
        }
      }
      result = Py_BuildValue("OII", bytes, w, h);
      Py_DECREF(bytes);
    }
    bmp->UnlockBits(&data);
  } else if (bmp->LockBits(&rect, ImageLockModeRead, PixelFormat32bppARGB,
                           &data) == Ok) {
    // 32bpp ARGB -> RGB
    size_t out_size = (size_t)w * h * 3;
    PyObject *bytes = PyBytes_FromStringAndSize(NULL, (Py_ssize_t)out_size);
    if (bytes) {
      uint8_t *dst = (uint8_t *)PyBytes_AS_STRING(bytes);
      for (UINT y = 0; y < h; ++y) {
        uint8_t *src = (uint8_t *)data.Scan0 + y * (size_t)data.Stride;
        for (UINT x = 0; x < w; ++x) {
          uint8_t b = src[x * 4 + 0];
          uint8_t g = src[x * 4 + 1];
          uint8_t r = src[x * 4 + 2];
          dst[(y * (size_t)w + x) * 3 + 0] = r;
          dst[(y * (size_t)w + x) * 3 + 1] = g;
          dst[(y * (size_t)w + x) * 3 + 2] = b;
        }
      }
      result = Py_BuildValue("OII", bytes, w, h);
      Py_DECREF(bytes);
    }
    bmp->UnlockBits(&data);
  } else {
    PyErr_SetString(PyExc_RuntimeError, "Unsupported pixel format");
  }
  delete bmp;
  GdiplusShutdown(token);
  return result;
}

static PyObject *py_save_png(PyObject *self, PyObject *args) {
  const char *path = NULL;
  PyObject *rgb_bytes = NULL;
  int width = 0, height = 0;
  if (!PyArg_ParseTuple(args, "sOii", &path, &rgb_bytes, &width, &height))
    return NULL;
  if (!PyBytes_Check(rgb_bytes)) {
    PyErr_SetString(PyExc_TypeError, "Second arg must be bytes (RGB)");
    return NULL;
  }
  Py_ssize_t size = PyBytes_GET_SIZE(rgb_bytes);
  if (size != (Py_ssize_t)width * height * 3) {
    PyErr_SetString(PyExc_ValueError, "Buffer size mismatch");
    return NULL;
  }
  ULONG_PTR token = 0;
  GdiplusStartupInput si;
  if (GdiplusStartup(&token, &si, NULL) != Ok) {
    PyErr_SetString(PyExc_RuntimeError, "GDI+ startup failed");
    return NULL;
  }
  Bitmap bmp((INT)width, (INT)height, PixelFormat32bppARGB);
  Rect rect(0, 0, (INT)width, (INT)height);
  BitmapData data;
  if (bmp.LockBits(&rect, ImageLockModeWrite, PixelFormat32bppARGB, &data) !=
      Ok) {
    GdiplusShutdown(token);
    PyErr_SetString(PyExc_RuntimeError, "LockBits failed");
    return NULL;
  }
  const uint8_t *src = (const uint8_t *)PyBytes_AS_STRING(rgb_bytes);
  for (int y = 0; y < height; ++y) {
    uint8_t *dst = (uint8_t *)data.Scan0 + y * (size_t)data.Stride;
    for (int x = 0; x < width; ++x) {
      const uint8_t *s = src + ((size_t)y * width + x) * 3;
      dst[x * 4 + 0] = s[2];
      dst[x * 4 + 1] = s[1];
      dst[x * 4 + 2] = s[0];
      dst[x * 4 + 3] = 255;
    }
  }
  bmp.UnlockBits(&data);
  CLSID clsidPng;
  UINT num = 0, sizeEnc = 0;
  GetImageEncodersSize(&num, &sizeEnc);
  std::unique_ptr<uint8_t[]> buf(new (std::nothrow) uint8_t[sizeEnc]);
  if (!buf) {
    GdiplusShutdown(token);
    PyErr_SetString(PyExc_MemoryError, "alloc");
    return NULL;
  }
  ImageCodecInfo *enc = (ImageCodecInfo *)buf.get();
  GetImageEncoders(num, sizeEnc, enc);
  bool found = false;
  for (UINT i = 0; i < num; ++i) {
    if (wcscmp(enc[i].MimeType, L"image/png") == 0) {
      clsidPng = enc[i].Clsid;
      found = true;
      break;
    }
  }
  PyObject *ret = NULL;
  if (found) {
    int need = MultiByteToWideChar(CP_UTF8, 0, path, -1, NULL, 0);
    if (need > 0) {
      std::unique_ptr<wchar_t[]> wpath(new (std::nothrow) wchar_t[need]);
      if (wpath &&
          MultiByteToWideChar(CP_UTF8, 0, path, -1, wpath.get(), need)) {
        Status st = bmp.Save(wpath.get(), &clsidPng, NULL);
        if (st == Ok) {
          ret = PyBool_FromLong(1);
        }
      }
    }
  }
  if (!ret)
    ret = PyBool_FromLong(0);
  GdiplusShutdown(token);
  return ret;
}

static PyObject *py_resize_image_rgb(PyObject *self, PyObject *args) {
  PyObject *rgb_bytes;
  int old_width, old_height, new_width, new_height;
  
  if (!PyArg_ParseTuple(args, "Oiiii", &rgb_bytes, &old_width, &old_height, &new_width, &new_height)) {
    return NULL;
  }
  
  if (!PyBytes_Check(rgb_bytes)) {
    PyErr_SetString(PyExc_TypeError, "Expected bytes object");
    return NULL;
  }
  
  Py_ssize_t old_size = PyBytes_Size(rgb_bytes);
  if (old_size != (Py_ssize_t)(old_width * old_height * 3)) {
    PyErr_SetString(PyExc_ValueError, "Input buffer size mismatch");
    return NULL;
  }
  
  // Create output buffer
  Py_ssize_t new_size = (Py_ssize_t)(new_width * new_height * 3);
  PyObject *result = PyBytes_FromStringAndSize(NULL, new_size);
  if (!result) {
    return NULL;
  }
  
  const uint8_t *src = (const uint8_t *)PyBytes_AS_STRING(rgb_bytes);
  uint8_t *dst = (uint8_t *)PyBytes_AS_STRING(result);
  
  // Simple nearest neighbor resize
  for (int new_y = 0; new_y < new_height; ++new_y) {
    int old_y = (new_y * old_height) / new_height;
    if (old_y >= old_height) old_y = old_height - 1;
    
    for (int new_x = 0; new_x < new_width; ++new_x) {
      int old_x = (new_x * old_width) / new_width;
      if (old_x >= old_width) old_x = old_width - 1;
      
      // Copy RGB pixel
      const uint8_t *src_pixel = src + (old_y * old_width + old_x) * 3;
      uint8_t *dst_pixel = dst + (new_y * new_width + new_x) * 3;
      
      dst_pixel[0] = src_pixel[0];  // R
      dst_pixel[1] = src_pixel[1];  // G
      dst_pixel[2] = src_pixel[2];  // B
    }
  }
  
  return result;
}

// load_image_rgb is already included in Methods above on Windows
#endif
