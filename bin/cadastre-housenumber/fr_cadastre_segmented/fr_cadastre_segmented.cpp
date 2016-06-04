
#include <Python.h>
#include <math.h>
#include <stdlib.h>
#include <assert.h>

#define CLASSIFIER_VECTOR_SIZE 46

static double vector_mean[CLASSIFIER_VECTOR_SIZE] = {
  0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
};

static double vector_scale[CLASSIFIER_VECTOR_SIZE] = {
  1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1
};


class Coords {
public:
  double x,y;
  Coords() {}
  Coords(double vx, double vy) : x(vx), y(vy) {}
  Coords(const Coords& copy) : x(copy.x), y(copy.y) {}
  bool operator !=(const Coords &b) const {
      return (this->x != b.x) || (this->y != b.y);
  }
  bool operator ==(const Coords &b) const {
      return (this->x == b.x) && (this->y == b.y);
  }
  Coords operator -(const Coords &b) const {
      return Coords(this->x - b.x, this->y - b.y);
  }
  double angle(const Coords &b) const {
      double d = this->norm() * b.norm();
      if (d == 0) {
          return 0;
      }
      double v = this->dot(b) / d;
      if (v > 1) v = 1;
      if (v < -1) v = -1;
      return acos(v);
  }
  double norm() const {
      return sqrt((this->x * this->x) + (this->y * this->y));
  }
  double dot(const Coords &b) const {
      return (this->x* b.x) + (this->y * b.y);
  }
  double dist(const Coords &b) const {
      return (b - *this).norm();
  }
};

static double
rad2deg(double rad) {
    return rad * 180 / M_PI;
}

static void
print(const Coords* coords, int size) {
   printf("(");
   for (int i=0;i<size;i++) {
     printf("%.1f %.1f", coords[i].x, coords[i].y);
     if (i+1<size) {
       printf(",  ");
     }
   }
   printf(")");
}

static int
find(const Coords* array, int size, const Coords value) {
    int i;
    for(i=0; i<size; i++) {
        if (array[i] == value) {
            return i;
        }
    }
    return -1;
}

static double
length(const Coords* coords, int size) {
    double length = 0;
    for(int i=0; i< (size-1); i++) {
        length += coords[i].dist(coords[i+1]);
    }
    return length;
}

static int
count(const char* s, char c)
{
  int count = 0;
  while(*s) count += (*s++ == c);
  return count;
}

static const char*
find(const char* s, char c) {
  while(*s && (*s != c)) s++;
  return (*s == c) ? s : NULL;
}

static int
wkt_coords_nb(const char* wkt) {
    return count(wkt, ',') + 1;
}



/**
 * Parse maximmum 'size' coordinates frow WKT string 's' having the format
 *   "... (x1 y1, x2 y2, x3 y3 ..."
 * storing it in the 'coords' array.
 */
static int
parse_wkt_coords(const char* s, Coords* coords, const int size)
{
  int i;
  s = find(s, '(');
  if (s == NULL) return 0;
  s = find(s+1, '(');
  for(i=0; i<size; i++) {
    if (s == NULL) return i; // separator not found
    s++; // after separator
    while(*s == ' ') s++; // skip spaces
    double x = atof(s);
    s = find(s, ' ');
    if (s == NULL) return i; // separator not found
    while(*s == ' ') s++; // skip spaces
    double y = atof(s);
    coords[i].x = x;
    coords[i].y = y;
    s = find(s, ',');
  }
  return size;
}

static void
reverse(Coords* coords, int size) {
    int middle = size/2;
    for(int i=0, j=size-1; i<middle; i++, j--) {
        Coords tmp = coords[i];
        coords[i] = coords[j];
        coords[j] = tmp;
    }
}

static void
shift_left(Coords* coords, int size, int shift) {
    if (shift > 0) {
        Coords tmp[shift];
        memcpy(tmp, coords, sizeof(Coords)*shift);
        memmove(coords, coords+shift, sizeof(Coords)*(size-shift));
        memcpy(coords+size-shift, tmp, sizeof(Coords)*shift);
    }
}

/**
 * Search for the common part betwwen poly1 and poly2
 * Then swith the poly1 and poly2 content so that they start with
 * the external part (the not common part), and then the common
 * part.
 * return the size of the common part.
 * ex: poly1 = [ a, b, c, d, a ] size1= 5 puis size1 = 4
 *     poly2 = [ e, f, g, b, c, h, i, j, e] size2 = 9 puis size2 = 8
 *     => return 2
 *         poly1 = [c, d, a, b, c]
 *         poly2 = [c, h, i, j, e, f, g, b, c]
 *
 * @return the size of the common part.
 *
 */
static int
shift_to_common_start_and_get_common_size(
        Coords* poly1, int size1,
        Coords* poly2, int size2)

{
    size1 = size1 - 1; // forget the last element identical to the 1st one
    size2 = size2 - 1; // forget the last element identical to the 1st one
    for(int i1=0, prev_i1 = size1-1; i1<size1; i1++) {
        int i2 = find(poly2, size2, poly1[i1]);
        if ((i2 >= 0) && (find(poly2, size2, poly1[prev_i1]) < 0)) {
            //printf("i1 = %d    i2 = %d\n", i1, i2);
            if ((poly2[(i2+1)%size2] == poly1[prev_i1])
                    || (poly2[(i2-1+size2)%size2] == poly1[(i1+1)%size1]))
            {
                reverse(poly2, size2);
                //printf("reverse poly2\n");
                //printf("poly2 = "); print(poly2, size2); printf("\n");
                i2 = size2 - 1 - i2;
                //printf("i1 = %d    i2 = %d\n", i1, i2);
            }
            //printf("shift_left\n");
            shift_left(poly1, size1, i1);
            shift_left(poly2, size2, i2);
            poly1[size1] = poly1[0]; // correct the closed way
            poly2[size2] = poly2[0]; // correct the closed way
            break;
        }
        prev_i1 = i1;
    }
    int common_size = 0;
    while((common_size < size1) && (common_size < size2)
            && (poly1[common_size] == poly2[common_size]))
    {
            common_size++;
    }
    return common_size;
}

static double
angle(const Coords &a, const Coords &b, const Coords &c)
{
    return (a-b).angle(c-b);
}

static double
diff_to_90(double a)
{
    return fabs(45 - fabs(45 - (fmod(a, 90.0))));
}

static void
get_angles(Coords &p0, Coords* poly, int size, Coords &pn, double* result)
{
    int i;
    if (size == 1) {
        result[0] = angle(p0, poly[0], pn);
    } else if (size > 1) {
        result[0] = angle(p0, poly[0], poly[1]);
        for(i=1; i<(size-1); i++) {
            result[i] = angle(poly[i-1], poly[i], poly[i+1]);
        }
        result[size-1] = angle(poly[size-2], poly[size-1], pn);
    }
    for(i=0; i<size;i++) {
        result[i] = rad2deg(result[i]);
    }
}


static void
compute_min_max_mean_std(
        const double* values, int size,
        double *out_min, double *out_max, double *out_mean, double *out_std)
{
    int i;
    if (size <= 0) {
        *out_min = 0;
        *out_max = 0;
        *out_mean = 0;
        *out_std = 0;
    } else {
        double v = values[0];
        double sum = v;
        double min = v;
        double max = v;
        for(i=1; i<size; i++) {
            v = values[i];
            sum += v;
            min = fmin(min, v);
            max = fmax(max, v);
        }
        double mean = sum / size;
        double variance = 0;
        for(i=0; i<size; i++) {
            v = values[i] - mean;
            variance += v*v;
        }
        variance = variance / size;
        *out_min = min;
        *out_max = max;
        *out_mean = mean;
        *out_std = sqrt(variance);
    }
}


/**
 * Fill in the calssifier vector 'clsfr_vec' with some statistics
 * two polygons represented by the coordinate coords1 and coords2
 * (of size size1 and size2 respectively).
 * @return 1 for success, 0 for failure.
 */
static int
fill_classifier_vector(double* clsfr_vec, Coords* poly1, int size1, Coords* poly2, int size2)
{
    int i = 0;
    if ((poly1[0] != poly1[size1-1]) || (poly2[0] != poly2[size2-1])) {
        return 0; // failure (not closed polygon)
    }

    //printf("poly1 = "); print(poly1, size1); printf("\n");
    //printf("poly2 = "); print(poly2, size2); printf("\n");

    int common_size = shift_to_common_start_and_get_common_size(
            poly1, size1, poly2, size2);

    //printf(" => common size = %d\n", common_size);
    //printf("poly1 = "); print(poly1, size1); printf("\n");
    //printf("poly2 = "); print(poly2, size2); printf("\n");

    // need at leas two common nodes to consider we have
    // a segmented building
    if (common_size < 2) {
        return 0;
    }

    //memset(clsfr_vec, 0, sizeof(clsfr_vec[0]) * CLASSIFIER_VECTOR_SIZE);

    Coords* common = poly1;

    Coords* external1 = poly1 + common_size - 1;
    int external1_size = size1 - common_size + 1;

    Coords* external2 = poly2 + common_size - 1;
    int external2_size = size2 - common_size + 1;

    //          a------b------------c
    //          |       \           |
    //          |        d          |
    //  poly1  ...       ...       ...  poly2
    //          |          e        |
    //          |           \       |
    //          f------------g------h
    //
    // =>
    //
    //              a---b              b            b---------c
    //              |                   \                     |
    //              |                    d                    |
    //  external1  ...           common  ...      external2  ...
    //              |                      e                  |
    //              |                       \                 |
    //              f---------g              g            g---h
    //
    // common = [b, d, ..., e, g]
    // external1 = [g, f, ..., a, b]
    // external2 = [g, h, ..., c, b]
    //
    Coords a = external1[external1_size-2];
    Coords b = common[0];
    Coords c = external2[external2_size-2];
    Coords d = common[1]; // == poly2[1]
    Coords e = common[common_size-2]; // == poly2[common_size-2];
    Coords f = external1[1];
    Coords g = common[common_size-1];
    Coords h = external2[1];

    int v=0;
    clsfr_vec[v++] = rad2deg(angle(a,b,c));
    clsfr_vec[v++] = rad2deg(angle(f,g,h));
    clsfr_vec[v++] = rad2deg(angle(a,b,d));
    clsfr_vec[v++] = rad2deg(angle(e,g,f));
    clsfr_vec[v++] = rad2deg(angle(c,b,d));
    clsfr_vec[v++] = rad2deg(angle(e,g,h));
    for(i=0; i<6;i++) {
        clsfr_vec[v++] = diff_to_90(clsfr_vec[i]) * 4;
    }


    // Compare common length ratio
    double common_length = length(poly1, common_size);
    double external1_length = length(external1, external1_size);
    double external2_length = length(external2, external2_size);
    double ratio1 = common_length / external1_length;
    double ratio2 = common_length / external2_length;
    if ((ratio1 < .05) && (ratio2 < .05)) {
        // Hard codded exclusion of segmented building
        // that have a really really small common part
        return 0;
    }
    clsfr_vec[v++] = atan(ratio1) / (M_PI/2) * 180;
    clsfr_vec[v++] = atan(ratio2) / (M_PI/2) * 180;



    double common1_extd_angles[common_size];
    double common2_extd_angles[common_size];
    double external1_extd_angles[external1_size];
    double external2_extd_angles[external2_size];
    // Extended common part as they are with the cut on each side,
    get_angles(a, common, common_size, f, common1_extd_angles);
    get_angles(c, common, common_size, h, common2_extd_angles);
    // Consider the external ways, as they would be without the cut:
    get_angles(h, external1, external1_size, c, external1_extd_angles);
    get_angles(f, external2, external2_size, a, external2_extd_angles);


    double common1_extd_angles_min = 0;
    double common1_extd_angles_max = 0;
    double common1_extd_angles_mean = 0;
    double common1_extd_angles_std = 0;
    double common2_extd_angles_min = 0;
    double common2_extd_angles_max = 0;
    double common2_extd_angles_mean = 0;
    double common2_extd_angles_std = 0;
    double external1_extd_angles_min = 0;
    double external1_extd_angles_max = 0;
    double external1_extd_angles_mean = 0;
    double external1_extd_angles_std = 0;
    double external2_extd_angles_min = 0;
    double external2_extd_angles_max = 0;
    double external2_extd_angles_mean = 0;
    double external2_extd_angles_std = 0;

    compute_min_max_mean_std(
        common1_extd_angles,
        common_size,
        &common1_extd_angles_min,
        &common1_extd_angles_max,
        &common1_extd_angles_mean,
        &common1_extd_angles_std);


    compute_min_max_mean_std(
        common2_extd_angles,
        common_size,
        &common2_extd_angles_min,
        &common2_extd_angles_max,
        &common2_extd_angles_mean,
        &common2_extd_angles_std);


    compute_min_max_mean_std(
        external1_extd_angles,
        external1_size,
        &external1_extd_angles_min,
        &external1_extd_angles_max,
        &external1_extd_angles_mean,
        &external1_extd_angles_std);


    compute_min_max_mean_std(
        external2_extd_angles,
        external2_size,
        &external2_extd_angles_min,
        &external2_extd_angles_max,
        &external2_extd_angles_mean,
        &external2_extd_angles_std);

    clsfr_vec[v++] = external1_extd_angles_mean,
    clsfr_vec[v++] = external1_extd_angles_std;
    clsfr_vec[v++] = external1_extd_angles_min;
    clsfr_vec[v++] = external1_extd_angles_max;
    clsfr_vec[v++] = external2_extd_angles_mean;
    clsfr_vec[v++] = external2_extd_angles_std;
    clsfr_vec[v++] = external2_extd_angles_min;
    clsfr_vec[v++] = external2_extd_angles_max;
    clsfr_vec[v++] = common1_extd_angles_mean - external1_extd_angles_mean;
    clsfr_vec[v++] = common1_extd_angles_std;
    clsfr_vec[v++] = common1_extd_angles_min - external1_extd_angles_min;
    clsfr_vec[v++] = common1_extd_angles_max - external1_extd_angles_max;
    clsfr_vec[v++] = common2_extd_angles_mean - external2_extd_angles_mean;
    clsfr_vec[v++] = common2_extd_angles_std;
    clsfr_vec[v++] = common2_extd_angles_min - external2_extd_angles_min;
    clsfr_vec[v++] = common2_extd_angles_max - external2_extd_angles_max;

    // Do the same with diff_to_90 angles

    for(i=0;i<common_size;i++) {
        common1_extd_angles[i] = diff_to_90(common1_extd_angles[i]);
        common2_extd_angles[i] = diff_to_90(common2_extd_angles[i]);
    }
    for(i=0;i<external1_size;i++) {
        external1_extd_angles[i] = diff_to_90(external1_extd_angles[i]);
    }
    for(i=0;i<external2_size;i++) {
        external2_extd_angles[i] = diff_to_90(external2_extd_angles[i]);
    }

    compute_min_max_mean_std(
        common1_extd_angles,
        common_size,
        &common1_extd_angles_min,
        &common1_extd_angles_max,
        &common1_extd_angles_mean,
        &common1_extd_angles_std);


    compute_min_max_mean_std(
        common2_extd_angles,
        common_size,
        &common2_extd_angles_min,
        &common2_extd_angles_max,
        &common2_extd_angles_mean,
        &common2_extd_angles_std);


    compute_min_max_mean_std(
        external1_extd_angles,
        external1_size,
        &external1_extd_angles_min,
        &external1_extd_angles_max,
        &external1_extd_angles_mean,
        &external1_extd_angles_std);


    compute_min_max_mean_std(
        external2_extd_angles,
        external2_size,
        &external2_extd_angles_min,
        &external2_extd_angles_max,
        &external2_extd_angles_mean,
        &external2_extd_angles_std);

    clsfr_vec[v++] = external1_extd_angles_mean,
    clsfr_vec[v++] = external1_extd_angles_std;
    clsfr_vec[v++] = external1_extd_angles_min;
    clsfr_vec[v++] = external1_extd_angles_max;
    clsfr_vec[v++] = external2_extd_angles_mean;
    clsfr_vec[v++] = external2_extd_angles_std;
    clsfr_vec[v++] = external2_extd_angles_min;
    clsfr_vec[v++] = external2_extd_angles_max;
    clsfr_vec[v++] = common1_extd_angles_mean - external1_extd_angles_mean;
    clsfr_vec[v++] = common1_extd_angles_std;
    clsfr_vec[v++] = common1_extd_angles_min - external1_extd_angles_min;
    clsfr_vec[v++] = common1_extd_angles_max - external1_extd_angles_max;
    clsfr_vec[v++] = common2_extd_angles_mean - external2_extd_angles_mean;
    clsfr_vec[v++] = common2_extd_angles_std;
    clsfr_vec[v++] = common2_extd_angles_min - external2_extd_angles_min;
    clsfr_vec[v++] = common2_extd_angles_max - external2_extd_angles_max;

    //printf("total size = %d\n", v);
    assert(v == CLASSIFIER_VECTOR_SIZE);

    for(i=0;i<v;i++) {
        clsfr_vec[i] = (clsfr_vec[i] - vector_mean[i]) * vector_scale[i];
    }
    return 1;
}


static PyObject*
double_array_to_python_list(const double* double_array, int size) {
  int i;
  PyObject *result_list = PyList_New(size);
  if (!result_list) return NULL;
  for(i=0; i < size; i++) {
        PyObject *num = PyFloat_FromDouble(double_array[i]);
        if (!num) {
            Py_DECREF(result_list);
            return NULL;
        }
        PyList_SET_ITEM(result_list, i, num);
  }
  return result_list;
}


static PyObject *
get_vector_length(PyObject *self, PyObject *args)
{
  return PyInt_FromLong(CLASSIFIER_VECTOR_SIZE);
}

static PyObject *
set_vector_mean_and_scale(PyObject *self, PyObject *args)
{ 
  PyObject * mean_list;  // arg1
  PyObject * scale_list; // arg2
  int i;
  if ((!PyArg_ParseTuple(args, "oo", &mean_list, &scale_list))
          || ( ! (PyList_Check(mean_list) && PyList_Check(scale_list)))
          || (PyList_Size(mean_list) <  CLASSIFIER_VECTOR_SIZE)
          || (PyList_Size(scale_list) <  CLASSIFIER_VECTOR_SIZE))
  {
    return NULL;
  }
  for(i=0; i<CLASSIFIER_VECTOR_SIZE; i++) {
      vector_mean[i] = PyFloat_AsDouble(PyList_GetItem(mean_list, i));
      vector_scale[i] = PyFloat_AsDouble(PyList_GetItem(scale_list, i));
  }
  Py_RETURN_NONE;
}

static PyObject *
get_classifier_vector(PyObject *self, PyObject *args)
{
  const char *wkt1; // arg1
  const char *wkt2; // arg2
  if (!PyArg_ParseTuple(args, "ss", &wkt1, &wkt2)) {
    return NULL;
  }

  int size1 = wkt_coords_nb(wkt1);
  int size2 = wkt_coords_nb(wkt2);
  Coords poly1[size1], poly2[size2];
  if (parse_wkt_coords(wkt1, poly1, size1) != size1) return NULL;
  if (parse_wkt_coords(wkt2, poly2, size2) != size2) return NULL;

  double classifier_vector[CLASSIFIER_VECTOR_SIZE];
  if (!fill_classifier_vector(classifier_vector, poly1, size1, poly2, size2))
  {
    Py_RETURN_NONE;
  }
  return double_array_to_python_list(
          classifier_vector, CLASSIFIER_VECTOR_SIZE);
}

static PyMethodDef cMethods[] = {
  {"get_classifier_vector", get_classifier_vector, METH_VARARGS,
   "Get statistic vector from 2 WKT Polygons representing 2 contiguous buildings potentially wrongly segmented"},
  {"set_vector_mean_and_scale", set_vector_mean_and_scale, METH_VARARGS,
   "Set 2 vectors representing min and max values so that subsequent call to get_classifier_vector will return values in the range [0 .. 1]"},
  {"get_vector_length", get_vector_length, METH_VARARGS,
   "Return the length of vectors"},
  {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initfr_cadastre_segmented(void)
{
  (void) Py_InitModule("fr_cadastre_segmented", cMethods);
}

