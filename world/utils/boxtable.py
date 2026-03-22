"""
Custom EvTable subclass with proper Unicode box-drawing character support.

This module provides a BoxTable class that extends EvTable to properly render
tables using Unicode box-drawing characters including proper T-junctions and
crosses at intersections.
"""

from evennia.utils.evtable import EvTable
from evennia.utils.ansi import ANSIString


def get_terminal_width(session=None):
    """
    Get terminal width from session, defaulting to 78 for MUD compatibility.
    
    Args:
        session: Evennia session object to get width from
        
    Returns:
        int: Terminal width in characters
    """
    if session:
        # Use Evennia's built-in screen width detection
        try:
            detected_width = session.protocol_flags.get("SCREENWIDTH", [78])[0]
            return max(60, detected_width)  # Minimum 60 for readability
        except (IndexError, KeyError, TypeError, AttributeError):
            # Fallback if protocol flags aren't available or malformed
            pass
    return 78


def center_text(text, width=None, session=None, fillchar=' '):
    """
    Center text within a given width, with automatic screen width detection.
    
    Args:
        text (str): Text to center (may include color codes)
        width (int, optional): Width to center within. If None, uses terminal width
        session: Evennia session object for width detection
        fillchar (str): Character to use for padding (default: space)
        
    Returns:
        str: Centered text with padding
    """
    if width is None:
        width = get_terminal_width(session)
    
    # Calculate visible length (excluding color codes)
    visible_text = ANSIString(text).clean()
    visible_len = len(visible_text)
    
    if visible_len >= width:
        return text
    
    # Calculate padding
    padding = (width - visible_len) // 2
    return fillchar * padding + text


class BoxTable(EvTable):
    """
    Custom EvTable that uses Unicode double-line box-drawing characters.
    
    This subclass overrides EvTable's border rendering to properly use
    double-line box-drawing characters including:
    - Corners: ╔ ╗ ╚ ╝
    - Lines: ═ ║
    - T-junctions: ╦ ╩ ╠ ╣
    - Cross: ╬
    
    Usage:
        from world.utils.boxtable import BoxTable
        
        table = BoxTable("Header1", "Header2", "Header3")
        table.add_row("data1", "data2", "data3")
        print(table)
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialize BoxTable with Unicode box-drawing characters.
        
        Args:
            *args: Column headers
            **kwargs: Same as EvTable, but border characters are preset
        """
        # Set default box-drawing characters (double-line style to match @stats)
        kwargs.setdefault('border', 'cells')
        kwargs.setdefault('border_left_char', '║')
        kwargs.setdefault('border_right_char', '║')
        kwargs.setdefault('border_top_char', '═')
        kwargs.setdefault('border_bottom_char', '═')
        kwargs.setdefault('corner_top_left_char', '╔')
        kwargs.setdefault('corner_top_right_char', '╗')
        kwargs.setdefault('corner_bottom_left_char', '╚')
        kwargs.setdefault('corner_bottom_right_char', '╝')
        kwargs.setdefault('header_line_char', '═')
        
        # Store border characters as instance attributes for later use
        self._border_left = kwargs['border_left_char']
        self._border_right = kwargs['border_right_char']
        self._border_top = kwargs['border_top_char']
        self._border_bottom = kwargs['border_bottom_char']
        self._corner_tl = kwargs['corner_top_left_char']
        self._corner_tr = kwargs['corner_top_right_char']
        self._corner_bl = kwargs['corner_bottom_left_char']
        self._corner_br = kwargs['corner_bottom_right_char']
        self._header_line = kwargs['header_line_char']
        
        # Initialize parent
        super().__init__(*args, **kwargs)
        
        # Store header title if provided
        self._header_title = None
        self._center_header = True  # Default to centering headers
    
    def add_header(self, title, center=True):
        """
        Add a centered title header above the table.
        
        Args:
            title (str): The title text to display
            center (bool): Whether to center the title (default: True)
        """
        self._header_title = title
        self._center_header = center
    
    def get_table_width(self):
        """
        Calculate the total width of the table based on its columns.
        
        Returns:
            int: Total width of the table in characters
        """
        # Force generation of table to get actual width
        table_output = super().__str__()
        if table_output:
            # Split into lines and get width of first line (border)
            lines = table_output.split('\n')
            if lines:
                # Get visible width excluding color codes
                return len(ANSIString(lines[0]).clean())
        return 78  # Fallback default
    
    def __str__(self):
        """
        Override string conversion to include header title if set.
        
        Returns:
            str: Table with optional centered header title
        """
        table_str = super().__str__()
        
        if self._header_title:
            # Get actual table width from rendered output
            lines = table_str.split('\n')
            if lines:
                table_width = len(ANSIString(lines[0]).clean())
            else:
                table_width = 78
            
            if self._center_header:
                # Center the title based on table width
                visible_len = len(ANSIString(self._header_title).clean())
                padding = (table_width - visible_len) // 2
                centered_title = " " * padding + self._header_title
            else:
                centered_title = self._header_title
            
            return f"{centered_title}\n{table_str}"
        
        return table_str
    
    def center_on_screen(self, screen_width=None, session=None):
        """
        Center the entire table on screen.
        
        Args:
            screen_width (int, optional): Width to center within. If None, auto-detect
            session: Evennia session for width detection
            
        Returns:
            str: Centered table output
        """
        if screen_width is None:
            screen_width = get_terminal_width(session)
        
        # Get the table output (without header, we'll add it after centering)
        has_header = self._header_title is not None
        header_text = self._header_title
        center_header = self._center_header
        
        # Temporarily remove header to get just the table
        self._header_title = None
        table_output = super().__str__()
        
        # Restore header for future calls
        self._header_title = header_text
        
        lines = table_output.split('\n')
        
        if not lines:
            return table_output
        
        # Calculate table width from first line
        table_width = len(ANSIString(lines[0]).clean())
        
        # Calculate left padding for centering
        if table_width >= screen_width:
            left_padding = 0  # Don't center if table is wider than screen
        else:
            left_padding = (screen_width - table_width) // 2
        
        padding_str = " " * left_padding
        
        # Add padding to each table line
        centered_lines = [padding_str + line for line in lines]
        
        # If we have a header, add it centered with the same padding
        if has_header:
            # Create a boxed header that matches the table style
            # The bottom border needs to connect with the table's top border
            
            # Get the table's first line (top border) - use the actual line with any color codes
            table_top_raw = lines[0] if lines else ""
            # Also get clean version for width calculation
            table_top_clean = ANSIString(table_top_raw).clean() if lines else ""
            
            # Create header box top border (same width as table)
            top_border = self._corner_tl + self._border_top * (table_width - 2) + self._corner_tr
            
            # Create header bottom border that connects with table top
            # This replaces the table's top border with proper T-junctions
            if table_top_clean:
                # Replace the first line (table top) to connect with header
                # Change corners to T-junctions: ╔ -> ╠, ╗ -> ╣
                # Keep the column separators (╦) as T-junctions pointing down (╦)
                bottom_border = table_top_clean.replace('╔', '╠').replace('╗', '╣')
                # Remove this line from centered_lines since we'll add it as part of header
                centered_lines.pop(0)
            else:
                # Fallback if no table top
                bottom_border = self._border_left + self._header_line * (table_width - 2) + self._border_right
            
            if center_header:
                # Center the header text within the box
                visible_len = len(ANSIString(header_text).clean())
                # Account for the border characters (║ on each side = 2 chars)
                inner_width = table_width - 2
                text_padding = (inner_width - visible_len) // 2
                right_padding = inner_width - visible_len - text_padding
                header_line = self._border_left + " " * text_padding + header_text + " " * right_padding + self._border_right
            else:
                # Left-align the header text within the box
                visible_len = len(ANSIString(header_text).clean())
                inner_width = table_width - 2
                right_padding = inner_width - visible_len - 1  # -1 for left padding
                header_line = self._border_left + " " + header_text + " " * right_padding + self._border_right
            
            # Add the screen left padding to all header lines
            boxed_header = [
                padding_str + top_border,
                padding_str + header_line,
                padding_str + bottom_border
            ]
            
            # Prepend boxed header to output (table top is already removed)
            for i, line in enumerate(boxed_header):
                centered_lines.insert(i, line)
        
        return '\n'.join(centered_lines)
    
    def _generate_lines(self):
        """
        Override line generation to fix T-junctions and crosses.
        
        This method post-processes the table output to replace incorrect
        corner characters at T-junctions with proper box-drawing characters.
        """
        # Get original lines from parent
        lines = list(super()._generate_lines())
        
        if not lines or len(lines) < 3:
            return lines
        
        # Process each line to fix intersections
        fixed_lines = []
        for i, line in enumerate(lines):
            line_str = str(line)
            
            # Fix T-junctions and crosses
            if i == 0:
                # Top line: replace + with ┬ for column junctions
                line_str = self._fix_top_line(line_str)
            elif i == len(lines) - 1:
                # Bottom line: replace + with ┴ for column junctions
                line_str = self._fix_bottom_line(line_str)
            else:
                # Middle lines: fix left/right edges and crosses
                line_str = self._fix_middle_line(line_str)
            
            fixed_lines.append(ANSIString(line_str))
        
        return fixed_lines
    
    def _fix_top_line(self, line):
        """
        Fix top line T-junctions.
        
        Replaces + characters (except corners) with ╦ for downward T-junctions.
        """
        if not line:
            return line
        
        # Convert to list for easy manipulation
        chars = list(line)
        
        # Find all + characters and replace with ╦ (except first and last)
        for i in range(1, len(chars) - 1):
            if chars[i] == '+':
                chars[i] = '╦'
        
        return ''.join(chars)
    
    def _fix_bottom_line(self, line):
        """
        Fix bottom line T-junctions.
        
        Replaces + characters (except corners) with ╩ for upward T-junctions.
        """
        if not line:
            return line
        
        # Convert to list for easy manipulation
        chars = list(line)
        
        # Find all + characters and replace with ╩ (except first and last)
        for i in range(1, len(chars) - 1):
            if chars[i] == '+':
                chars[i] = '╩'
        
        return ''.join(chars)
    
    def _fix_middle_line(self, line):
        """
        Fix middle line intersections.
        
        Replaces:
        - + at start of line with ╠
        - + at end of line with ╣
        - + in middle with ╬
        """
        if not line:
            return line
        
        # Convert to list for easy manipulation
        chars = list(line)
        
        # Fix left edge T-junction
        if len(chars) > 0 and chars[0] == '+':
            chars[0] = '╠'
        
        # Fix right edge T-junction
        if len(chars) > 1 and chars[-1] == '+':
            chars[-1] = '╣'
        
        # Fix internal crosses
        for i in range(1, len(chars) - 1):
            if chars[i] == '+':
                chars[i] = '╬'
        
        return ''.join(chars)


class SimpleBoxTable(EvTable):
    """
    Simplified BoxTable without internal column/row borders.
    
    This creates a clean table with just an outer box and header separator.
    Useful for cleaner displays without grid lines.
    
    Usage:
        from world.utils.boxtable import SimpleBoxTable
        
        table = SimpleBoxTable("Header1", "Header2")
        table.add_row("data1", "data2")
        print(table)
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialize SimpleBoxTable with outer box and header line only.
        
        Args:
            *args: Column headers
            **kwargs: Same as EvTable
        """
        # Set default box-drawing characters for simple box
        kwargs.setdefault('border', 'table')  # Only outer border
        kwargs.setdefault('border_left_char', '│')
        kwargs.setdefault('border_right_char', '│')
        kwargs.setdefault('border_top_char', '─')
        kwargs.setdefault('border_bottom_char', '─')
        kwargs.setdefault('corner_top_left_char', '┌')
        kwargs.setdefault('corner_top_right_char', '┐')
        kwargs.setdefault('corner_bottom_left_char', '└')
        kwargs.setdefault('corner_bottom_right_char', '┘')
        kwargs.setdefault('header_line_char', '─')
        
        # Initialize parent
        super().__init__(*args, **kwargs)
    
    def _generate_lines(self):
        """
        Override to add header line to 'table' border style.
        
        The 'table' border style doesn't include a header line by default,
        so we add it manually.
        """
        lines = list(super()._generate_lines())
        
        if not lines or len(lines) < 3 or not self.header:
            return lines
        
        # Insert header line after the first data row (after header row)
        # Find the width of the table
        if lines:
            table_width = len(ANSIString(str(lines[0])).clean())
            header_line = '├' + '─' * (table_width - 2) + '┤'
            
            # Insert after second line (header row)
            if len(lines) > 2:
                lines.insert(2, ANSIString(header_line))
        
        return lines
