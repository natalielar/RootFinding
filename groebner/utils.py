# A collection of functions used in the F4 and Macaulay solvers
import numpy as np
from scipy.linalg import lu, qr, solve_triangular
import heapq
import itertools
import time

class InstabilityWarning(Warning):
    pass

class TVBError(RuntimeError):
    pass

class Term(object):
    '''
    Terms are just tuples of exponents with the grevlex ordering
    '''
    def __init__(self,val):
        self.val = tuple(val)

    def __repr__(self):
        return str(self.val) + ' with grevlex order'

    def __lt__(self, other, order = 'grevlex'):
        '''
        Redfine less-than according to grevlex
        '''
        if order == 'grevlex': #Graded Reverse Lexographical Order
            if sum(self.val) < sum(other.val):
                return True
            elif sum(self.val) > sum(other.val):
                return False
            else:
                for i,j in zip(reversed(self.val),reversed(other.val)):
                    if i < j:
                        return False
                    if i > j:
                        return True
                return False
        elif order == 'lexographic': #Lexographical Order
            for i,j in zip(self.val,other.val):
                if i < j:
                    return True
                if i > j:
                    return False
            return False
        elif order == 'grlex': #Graded Lexographical Order
            if sum(self.val) < sum(other.val):
                return True
            elif sum(self.val) > sum(other.val):
                return False
            else:
                for i,j in zip(self.val,other.val):
                    if i < j:
                        return True
                    if i > j:
                        return False
                return False

    # Define the other relations in grevlex order

    def __eq__(self, other):
        return self.val == other.val

    def __gt__(self, other):
        return not(self < other or self == other)

    def __ge__(self, other):
        return (self > other or self == other)

    def __le__(self,other):
        return (self < other or self == other)

    #Makes terms hashable so they can go in a set
    def __hash__(self):
        return hash(self.val)

def clean_zeros_from_matrix(array, accuracy=1.e-10):
    '''Sets all values in the array less than the given accuracy to 0.

    Parameters
    ----------
    array : numpy array
    accuracy : float, optional
        Values in the matrix less than this will be set to 0.

    Returns
    -------
    array : numpy array
        Same array, but with values less than the given accuracy set to 0.
    '''
    array[(array < accuracy) & (array > -accuracy)] = 0
    return array

def divides(mon1, mon2):
    '''
    parameters
    ----------
    mon1 : tuple
        contains the exponents of the monomial divisor
    mon2 : tuple
        contains the exponents of the monomial dividend

    returns
    -------
    boolean
        true if mon1 divides mon2, false otherwise
    '''
    return np.all(np.subtract(mon2, mon1) >= 0)

def inverse_P(P):
    '''The inverse of P, the array with column switching indexes.

    Parameters
    ----------
    P : array-like
        1D array P returned by scipy's QRP decomposition.

    Returns
    -------
    1D numpy array
        The indexes needed to switch the columns back to their original
        positions.

    See Also
    --------
    scipy.linalg.qr : QR decomposition (with pivoting=True).

    '''
    inverse = [0] * len(P)
    for i, p in enumerate(P):
        inverse[p] = i
    return inverse    

def lcm(a,b):
    '''Finds the LCM of the two leading terms of polynomials a and b

    Parameters
    ----------
    a, b : polynomial objects

    Returns
    -------
    numpy array
        The lcm of the leading terms of a and b. The usual representation is
        used, i.e., :math:`x^2y^3` is represented as :math:`\mathtt{(2,3)}`
    '''
    return np.maximum(a.lead_term, b.lead_term)

def quotient(a, b):
    '''Finds the quotient of monomials a and b, that is, a / b.

    Parameters
    ----------
    a, b : array-like, the monomials to divide

    Returns
    -------
    list
        The quotient a / b
    '''
    return np.subtract(a,b)

def rrqr_reduce(matrix, clean = False, global_accuracy = 1.e-10):
    '''
    Reduces the matrix into row echelon form, so each row has a unique leading term.

    Parameters
    ----------
    matrix : (2D numpy array)
        The matrix of interest.
    clean: bool
        Defaults to False. If True then at certain points in the code all the points in the matrix
        that are close to 0 are set to 0.
    global_accuracy: float
        Defaults to 1.e-10. What is determined to be zero when searching for the pivot columns or setting
        things to zero.

    Returns
    -------
    matrix : (2D numpy array)
        The reduced matrix in row echelon form. It should look like this.
        a - - - - - - -
        0 b - - - - - -
        0 0 0 c - - - -
        0 0 0 0 d - - -
        0 0 0 0 0 0 0 e
    '''
    if matrix.shape[0]==0 or matrix.shape[1]==0:
        return matrix
    height = matrix.shape[0]
    A = matrix[:height,:height] #Get the square submatrix
    B = matrix[:,height:] #The rest of the matrix to the right
    Q,R,P = qr(A, pivoting = True) #rrqr reduce it
    PT = inverse_P(P)
    diagonals = np.diagonal(R) #Go along the diagonals to find the rank
    rank = np.sum(np.abs(diagonals)>global_accuracy)
    if rank == height: #full rank, do qr on it
        Q,R = qr(A)
        A = R #qr reduce A
        B = Q.T.dot(B) #Transform B the same way
    else: #not full rank
        A = R[:,PT] #Switch the columns back
        if clean:
            Q = np.clean_zeros_from_matrix(Q)
        B = Q.T.dot(B) #Multiply B by Q transpose
        if clean:
            B = np.clean_zeros_from_matrix(B)
        #sub1 is the top part of the matrix, we will recursively reduce this
        #sub2 is the bottom part of A, we will set this all to 0
        #sub3 is the bottom part of B, we will recursively reduce this.
        #All submatrices are then put back in the matrix and it is returned.
        sub1 = np.hstack((A[:rank,],B[:rank,])) #Takes the top parts of A and B
        result = rrqr_reduce(sub1) #Reduces it
        A[:rank,] = result[:,:height] #Puts the A part back in A
        B[:rank,] = result[:,height:] #And the B part back in B

        sub2 = A[rank:,]
        zeros = np.zeros_like(sub2)
        A[rank:,] = np.zeros_like(sub2)

        sub3 = B[rank:,]
        B[rank:,] = rrqr_reduce(sub3)

    reduced_matrix = np.hstack((A,B))
    return reduced_matrix

def rrqr_reduce2(matrix, clean = True, global_accuracy = 1.e-10):
    '''
    Reduces the matrix into row echelon form, so each row has a unique leading term.
    Note that it preforms the same function as rrqr_reduce, currently I'm not sure which is better.

    Parameters
    ----------
    matrix : (2D numpy array)
        The matrix of interest.
    clean: bool
        Defaults to True. If True then at certain points in the code all the points in the matrix
        that are close to 0 are set to 0.
    global_accuracy: float
        Defaults to 1.e-10. What is determined to be zero when searching for the pivot columns or setting
        things to zero.

    Returns
    -------
    matrix : (2D numpy array)
        The reduced matrix in row echelon form. It should look like this.
        a - - - - - - -
        0 b - - - - - -
        0 0 0 c - - - -
        0 0 0 0 d - - -
        0 0 0 0 0 0 0 e
    '''
    if matrix.shape[0] <= 1 or matrix.shape[0]==1 or  matrix.shape[1]==0:
        return matrix
    height = matrix.shape[0]
    A = matrix[:height,:height] #Get the square submatrix
    B = matrix[:,height:] #The rest of the matrix to the right
    independentRows, dependentRows, Q = row_linear_dependencies(A, accuracy = global_accuracy)
    nullSpaceSize = len(dependentRows)
    if nullSpaceSize == 0: #A is full rank
        Q,R = qr(matrix)
        return clean_zeros_from_matrix(R)
    else: #A is not full rank
        #sub1 is the independentRows of the matrix, we will recursively reduce this
        #sub2 is the dependentRows of A, we will set this all to 0
        #sub3 is the dependentRows of Q.T@B, we will recursively reduce this.
        #We then return sub1 stacked on top of sub2+sub3
        if clean:
            Q = clean_zeros_from_matrix(Q)
        bottom = matrix[dependentRows]
        sub3 = bottom[:,height:]
        sub3 = Q.T[-nullSpaceSize:]@B
        if clean:
            sub3 = clean_zeros_from_matrix(sub3)
        sub3 = rrqr_reduce2(sub3)

        sub1 = matrix[independentRows]
        sub1 = rrqr_reduce2(sub1)

        sub2 = bottom[:,:height]
        sub2[:] = np.zeros_like(sub2)

        reduced_matrix = np.vstack((sub1,np.hstack((sub2,sub3))))
        if clean:
            return clean_zeros_from_matrix(reduced_matrix)
        else:
            return reduced_matrix

def sorted_polys_coeff(polys):
    '''Sorts the polynomials by how much bigger the leading coefficient is than
    the rest of the coeff matrix.

    Parameters
    ----------
    polys : array-like
        Contains polynomial objects to sort.

    Returns
    -------
    sorted_polys : list
        The polynomial objects in order of lead coefficient to everything else
        ratio.
    '''
    # The lead_coeff to other stuff ratio.
    lead_coeffs = [abs(poly.lead_coeff)/np.sum(np.abs(poly.coeff)) for poly in polys]
    argsort_list = np.argsort(lead_coeffs)[::-1]
    sorted_polys = [polys[i] for i in argsort_list]
    return sorted_polys

def sorted_polys_monomial(polys):
    '''Sorts the polynomials by the number of monomials they have, the ones
    with the least amount first.

    Parameters
    ----------
    polys : array-like, contains polynomial objects !!! Is it a list or could it be any iterable?
        Polynomials to be sorted

    Returns
    -------
    sorted_polys : list
        Polynomials in order.
    '''
    # A list to contain the number of monomials with non zero coefficients.
    num_monomials = []
    for poly in polys:
        # This gets the length of the list of first indexes, since
        # that is number of non-zero coefficients in the coefficient array.
        # See documentation for np.where
        num_monomials.append(len(np.where(poly.coeff != 0)[0]))

    # Generate a sorted index based on num_monomials.
    argsort_list = np.argsort(num_monomials)
    sorted_polys = [polys[i] for i in argsort_list]
    return sorted_polys

def row_swap_matrix(matrix):
    '''Rearrange the rows of matrix so it is close to upper traingular.

    Parameters
    ----------
    matrix : 2D numpy array
        The matrix whose rows need to be switched

    Returns
    -------
    2D numpy array
        The same matrix but with the rows changed so it is close to upper
        triangular

    Examples
    --------
    >>> utils.row_swap_matrix(np.array([[0,2,0,2],[0,1,3,0],[1,2,3,4]]))
    array([[1, 2, 3, 4],
           [0, 2, 0, 2],
           [0, 1, 3, 0]])
    '''
    leading_mon_columns = list()
    for row in matrix:
        leading_mon_columns.append(np.where(row!=0)[0][0])

    return matrix[np.argsort(leading_mon_columns)]

def get_var_list(dim):
    '''Returns a list of the variables [x_1, x_2, ..., x_n] as tuples.'''
    _vars = []
    var = [0]*dim
    for i in range(dim):
        var[i] = 1
        _vars.append(tuple(var))
        var[i] = 0
    return _vars

def row_linear_dependencies(matrix, accuracy=1.e-10):
    '''
    Uses rank revealing QR to determine which rows of the given matrix are
    linearly independent and which ones are linearly dependent. (This
    function needs a name change).

    Parameters
    ----------
    matrix : (2D numpy array)
        The matrix of interest.

    Returns
    -------
    independentRows : (list)
        The indexes of the rows that are linearly independent
    dependentRows : (list)
        The indexes of the rows that can be removed without affecting the rank
        (which are the linearly dependent rows).
    Q : (2D numpy array)
        The Q matrix used in RRQR reduction in finding the rank.
    '''
    height = matrix.shape[0]
    Q,R,P = qr(matrix, pivoting = True)
    diagonals = np.diagonal(R) #Go along the diagonals to find the rank
    rank = np.sum(np.abs(diagonals)>accuracy)
    numMissing = height - rank
    if numMissing == 0: # Full Rank. All rows independent
        return [i for i in range(height)],[],None
    else:
        # Find the rows we can take out. These are ones that are non-zero in
        # the last rows of Q transpose, since QT*A=R.
        # To find multiple, we find the pivot columns of Q.T
        QMatrix = Q.T[-numMissing:]
        Q1,R1,P1 = qr(QMatrix, pivoting = True)
        independentRows = P1[R1.shape[0]:] #Other Columns
        dependentRows = P1[:R1.shape[0]] #Pivot Columns
        return independentRows, dependentRows, Q

def triangular_solve(matrix):
    """
    Takes a matrix that is in row echelon form and reduces it into row reduced echelon form.

    Parameters
    ----------
    matrix : 2D numpy array
        The matrix of interest.

    Returns
    -------
    matrix : 2D numpy array
        The matrix is row reduced echelon form.
    """
    m,n = matrix.shape
    j = 0  # The row index.
    k = 0  # The column index.
    order_c = [] # List to keep track of original index of the columns in c.
    order_d = [] # List to keep track of the original index of the columns in d.
    
    # Checks if the given matrix is not a square matrix.
    if m != n:
        # Makes sure the indicies are within the matrix.
        while j < m and k < n:
            if matrix[j,k] != 0:
                order_c.append(k)
                # Move to the diagonal if the index is non-zero.
                j+=1
                k+=1
            else:
                order_d.append(k)
                # Check the next column in the same row if index is zero.
                k+=1
        # Append the index of the rest of the columns to the order_d list.
        order_d += list(np.arange(k,n))
                
        # C will be the square matrix that is upper triangular with no zeros on the diagonals.
        C = matrix[:,order_c]
        
        # D is the rest of the columns.
        D = matrix[:,order_d]

        # Solve for the CX = D
        X = solve_triangular(C,D)

        # Add I to X. [I|X]
        solver = np.hstack((np.eye(X.shape[0]),X))
        
        # Reverse the columns back.
        solver = solver[:,inverse_P(order_c+order_d)]

        return solver
    else:
    # The case where the matrix passed in is a square matrix
        return np.eye(m)

def first_x(string):
    '''
    Finds the first position of an 'x' in a string. If there is not x it returns the length
    of the string.

    Parameters
    ----------
    string : str
        The string of interest.
    Returns
    -------
    i : int
        The position in the string of the first 'x' character. If 'x' does not appear in the string
        the return value is the length of the string.
    '''
    for i in range(len(string)):
        if string[i] == 'x':
            return i
    return len(string)

def is_number(string):
    '''
    Checks is a string can be converted to a number.
    Parameters
    ----------
    string : str
        The string of interest.
    Returns
    -------
    value : bool
        Whether or not the string is a valid number.
    '''
    try:
        float(string)
        return True
    except ValueError:
        return False

def makePolyCoeffMatrix(inputString):
    '''
    Takes a string input of a polynomaial and returns the coefficient matrix for it. Usefull for making things of high
    degree of dimension so you don't have to make it by hand.

    All strings must be of the following syntax. Ex. '3x0^2+2.1x1^2*x2+-14.73x0*x2^3'

    1. There can be no spaces.
    2. All monomials must be seperated by a '+'. If the coefficient of the monomial is negative then the '-' sign
       should come after the '+'. This is not needed for the first monomial.
    3. All variables inside a monomial are seperated by a '*'.
    4. The power of a variable in a monomial is given folowing a '^' sign.
    '''
    matrixSpots = list()
    coefficients = list()
    for monomial in inputString.split('+'):
        coefficientString = monomial[:first_x(monomial)]
        if coefficientString == '-':
            coefficient = -1
        elif coefficientString == '':
            coefficient = 1
        else:
            coefficient = float(coefficientString)
        mons = monomial[first_x(monomial):].split('*')
        matrixSpot = [0]
        for mon in mons:
            stuff = mon.split('^')
            if len(stuff) == 1:
                power = 1
            else:
                power = int(stuff[1])
            if stuff[0] == '':
                varDegree = -1
            else:
                varDegree = int(stuff[0][1:])
            if varDegree != -1:
                if len(matrixSpot) <= varDegree:
                    matrixSpot = np.append(matrixSpot, [0]*(varDegree - len(matrixSpot)+1))
                matrixSpot[varDegree] = power
        matrixSpots.append(matrixSpot)
        coefficients.append(coefficient)

    #Pad the matrix spots so they are all the same length.
    length = max(len(matrixSpot) for matrixSpot in matrixSpots)
    for i in range(len(matrixSpots)):
        matrixSpot = matrixSpots[i]
        if len(matrixSpot) < length:
            matrixSpot = np.append(matrixSpot, [0]*(length - len(matrixSpot)))
            matrixSpots[i] = matrixSpot
    matrixSize = np.maximum.reduce([matrixSpot for matrixSpot in matrixSpots])
    matrixSize = matrixSize + np.ones_like(matrixSize)
    matrix = np.zeros(matrixSize)
    for i in range(len(matrixSpots)):
        matrixSpot = matrixSpots[i]
        coefficient = coefficients[i]
        matrix[tuple(matrixSpot)] = coefficient
    return matrix

def slice_top(matrix):
    ''' Gets the n-d slices needed to slice a matrix into the top corner of another.
    
    Parameters
    ----------
    coeff : numpy matrix.
        The matrix of interest.
    Returns
    -------
    slices : list
        Each value of the list is a slice of the matrix in some dimension. It is exactly the size of the matrix.
    '''
    slices = list()
    for i in matrix.shape:
        slices.append(slice(0,i))
    return slices

def slice_bottom(matrix):
    ''' Gets the n-d slices needed to slice a matrix into the bottom corner of another.
    
    Parameters
    ----------
    coeff : numpy matrix.
        The matrix of interest.
    Returns
    -------
    slices : list
        Each value of the list is a slice of the matrix in some dimension. It is exactly the size of the matrix.
    '''
    slices = list()
    for i in matrix.shape:
        slices.append(slice(-i,None))
    return slices

def match_size(a,b):
    '''
    Matches the shape of two matrixes. 

    Parameters
    ----------
    a, b : ndarray
        Matrixes whose size is to be matched.

    Returns
    -------
    a, b : ndarray
        Matrixes of equal size and dimension.
    '''
    a_shape, b_shape = list(a.shape), list(b.shape)
    if len(a_shape) != len(b_shape): #Makes the dimension sizes equal.
        add_to_shape = 0
        if len(a_shape) < len(b_shape):
            add_to_shape = len(b_shape) - len(a_shape)
            for i in range(add_to_shape):
                a_shape.insert(0,1)
            a = a.reshape(a_shape)
        else:
            add_to_shape = len(a_shape) - len(b_shape)
            for i in range(add_to_shape):
                b_shape.insert(0,1)
            b = b.reshape(b_shape)

    new_shape = np.maximum(a.shape, b.shape)
    
    a_new = np.zeros(new_shape)
    a_new[slice_top(a)] = a
    b_new = np.zeros(new_shape)
    b_new[slice_top(b)] = b
    return a_new, b_new