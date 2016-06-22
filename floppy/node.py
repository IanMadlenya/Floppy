from collections import OrderedDict
from copy import copy
from floppy.FloppyTypes import Type, MetaType

NODECLASSES = {}


class InputNotAvailable(Exception):
    pass


class InputAlreadySet(Exception):
    pass


def abstractNode(cls):
    """
    Removes a Node class from the NODECLASSES dictionary and then returns the class object.
    Use this as a decorator to stop a not fully implemented Node class from being available in the editor.
    :param cls: Node class object.
    :return: Unmodified node class object.
    :rtype: Node
    """
    del NODECLASSES[cls.__name__]
    return cls


class Info(object):
    """
    Class for handling all information related to both inputs and outputs.
    """
    def __init__(self, name, varType, hints=None, default='', select=None, owner=False, list=False):
        self.name = name
        self.connected = False
        self.varType = varType
        if not hints:
            self.hints = [varType.__name__]
        else:
            self.hints = [varType.__name__] + hints
        self.default = default
        self.valueSet = False
        self.value = None
        self.select = select
        self.owner = owner
        self.list = list

    def setOwner(self, owner):
        self.owner = owner

    def setDefault(self, value):
        if not self.varType == object and not issubclass(self.varType, Type):
            try:
                self.default = self.varType(value)
            except ValueError:
                self.default = ''
            if self.varType == bool:
                try:
                    if value.upper() == 'TRUE':
                        self.default = True
                    else:
                        self.default = False
                except:
                    self.default = value
        else:
            self.default = value

    def __str__(self):
        return 'INFO'

    def reset(self):
        self.default = None
        self.valueSet = False
        self.value = None


class InputInfo(Info):
    def __call__(self, noException=False):
        if self.valueSet:
            if not self.varType == object:
                if isinstance(self.varType, MetaType):
                    if self.list:
                        return [self.varType.checkType(i) for i in self.value]
                    return self.varType.checkType(self.value)
                else:
                    if self.list:
                        return [self.varType(i) for i in self.value]
                    return self.varType(self.value)
            else:
                return self.value
        elif self.default != None and not self.connected:
            if not self.varType == object:
                return self.varType(self.default)
            else:
                return self.default
        else:
            if noException:
                return None
            else:
                raise InputNotAvailable('Input not set for node.')

    def set(self, value, override=False):
        if self.valueSet and not override:
            raise InputAlreadySet('Input \'{}\' of node \'{}\' is already set.'.format(self.name, str(self.owner)))
        self.value = value
        self.valueSet = True

    def setConnected(self, value: bool):
        self.connected = value

    def isAvailable(self):
        if self.valueSet:
            return True
        elif self.default != None and not self.connected:
            return True
        return False


class OutputInfo(Info):
    def __call__(self, value):
        try:
            value.__FloppyType__ = self.varType
        except AttributeError:
            pass
        self.value = value
        self.valueSet = True


class MetaNode(type):
    """
    Meta class for the Node class. Makes node declaration objects available in the class's scope and registers each
    Node object to have a convenient way of accessing all subclasses of Node.
    """
    inputs = []
    outputs = []

    @classmethod
    def __prepare__(metacls, name, bases):
        MetaNode.inputs = []
        MetaNode.outputs = []
        MetaNode.tags = []
        return {'Input': MetaNode.addInput,
                'input': MetaNode.addInput,
                'Output': MetaNode.addOutput,
                'output': MetaNode.addOutput,
                'Tag': MetaNode.addTag,
                'tag': MetaNode.addTag}

    def addTag(*args):
        for arg in args:
            MetaNode.tags.append(arg)


    def addInput(name: str,
                 varType: object,
                 hints=None,
                 default='',
                 select=None,
                 list=False):
        MetaNode.inputs.append({'name': name,
                                'varType': varType,
                                'hints': hints,
                                'default': default,
                                'select': select,
                                'list': list})

    def addOutput(name: str,
                  varType: object,
                  hints=None,
                  default='',
                  select=None,
                  list=False):
        MetaNode.outputs.append({'name': name,
                                 'varType': varType,
                                 'hints': hints,
                                 'default': default,
                                 'select': select,
                                 'list': list})

    def __new__(cls, name, bases, classdict):
        result = type.__new__(cls, name, bases, classdict)
        # result.__dict__['Input'] = result._addInput
        NODECLASSES[name] = result
        try:
            result.__inputs__ = result.__bases__[0].__inputs__.copy()
        except AttributeError:
            result.__inputs__ = OrderedDict()
        try:
            result.__outputs__ = result.__bases__[0].__outputs__.copy()
        except AttributeError:
            result.__outputs__ = OrderedDict()

        try:
            result.__tags__ = result.__bases__[0].__tags__.copy()
        except AttributeError:
            result.__tags__ = []

        for inp in MetaNode.inputs:
            result._addInput(data=inp, cls=result)

        for out in MetaNode.outputs:
            result._addOutput(data=out, cls=result)

        for tag in MetaNode.tags:
            result._addTag(tag)
        return result

@abstractNode
class Node(object, metaclass=MetaNode):
    """
    Base class for Nodes.

    To add Inputs to a custom Node class call 'Input(name, varType, hints, list)' in the class's
    body e.g.:

        class MyNode(Node):
            Input('myStringInput', str, list=True)

    To access the value of an input during the Node's 'run' method or 'check' method use
    'myNodeInstance._myStringInput'. An 'InputNotAvailable' Exception is raised is the input is not set yet.
    """
    Tag('Node')

    def __init__(self, nodeID, graph):
        self.__pos__ = (0, 0)
        self.graph = graph
        self.ID = nodeID
        self.inputs = OrderedDict()
        self.outputs = OrderedDict()
        self.inputPins = OrderedDict()
        self.outputPins = OrderedDict()
        for i, inp in enumerate(self.__inputs__.values()):
            inp = copy(inp)
            inp.setOwner(self)
            inpID = '{}:I{}'.format(self.ID, inp.name)
            newPin = Pin(inpID, inp, self)
            self.inputPins[inp.name] = newPin
            self.inputs[inp.name] = inp

        for i, out in enumerate(self.__outputs__.values()):
            out = copy(out)
            out.setOwner(self)
            outID = '{}:O{}'.format(self.ID, out.name)
            newPin = Pin(outID, out, self)
            self.outputPins[out.name] = newPin
            self.outputs[out.name] = out
        if not self.inputs.keys():
            raise AttributeError('Nodes without any input are not valid.')

    def __str__(self):
        return '{}-{}'.format(self.__class__.__name__, self.ID)

    def __hash__(self):
        return hash(str(self))

    def run(self) -> None:
        """
        Execute the node. Override this to implement logic.
        :rtype: None
        """
        print('Executing node {}'.format(self))

    def notify(self):
        """
        Manage the node's state after execution and set input values of subsequent nodes.
        :return: None
        :rtype: None
        """
        for con in self.graph.getConnectionsFrom(self):
            outputName = con['outputName']
            nextNode = con['inputNode']
            nextInput = con['inputName']
            # nextNode.prepare()
            if self.outputs[outputName].valueSet:
                nextNode.setInput(nextInput, self.outputs[outputName].value, override=True)
            else:
                nextNode.setInput(nextInput, self.outputs[outputName].default, override=True)

        [Info.reset(inp) for inp in self.inputs.values()]

    def setInput(self, inputName, value, override=False):
        """
        Sets the value of an input.
        :param inputName: str representing the name of the input.
        :param value: object of the appropriate type for that input.
        :param override: boolean specifying whether the input should be overridden if it was set already.
        :return: None
        """
        self.inputs[inputName].set(value, override=override)

    def check(self) -> bool:
        """
        Checks whether all prerequisites for executing the node instance are met.
        Override this to implement custom behavior.
        By default the methods returns True if all inputs have been set. False otherwise.
        :return: Boolean; True if ready, False if not ready.
        :rtype: bool
        """
        for inp in self.inputs.values():
            if not inp.isAvailable():
                print('        {}: Prerequisites not met.'.format(str(self)))
                return False
        return True

    # def prepare(self):
    #     """
    #     Method for preparing a node for execution.
    #     This method is called on each node before the main execution loop of the owning graph instance is started.
    #     The methods makes sure that artifacts from previous execution are reset to their original states and default
    #     values of inputs that are connected to other nodes' outputs are removed.
    #     :return:
    #     """
    #     return
    #     [InputInfo.reset(inp) for inp in self.inputs.values()]

    def _addInput(*args, data='', cls=None):
        """
        This should be a classmethod.
        :param args:
        :param data:
        :param cls:
        :return:
        """
        inputInfo = InputInfo(**data)
        cls.__inputs__[data['name']] = inputInfo

    def _addOutput(*args, data='', cls=None):
        """
        This should be a classmethod.
        :param args:
        :param data:
        :param cls:
        :return:
        """
        outputInfo = OutputInfo(**data)
        cls.__outputs__[data['name']] = outputInfo

    @classmethod
    def _addTag(cls, tag='Node'):
        """
        Adds a Tag to a Node class object.
        :param tag:
        :return:
        """
        cls.__tags__.append(tag)

    def __getattr__(self, item):
        """
        Catches self._<Input/Ouptput> accesses and calls the appropriate methods.
        :param item: str; Attribute name.
        :return: object; Attribute
        :rtype: object
        """
        if item.startswith('_') and not item.startswith('__'):
            try:
                return self.inputs[item.lstrip('_')]()
            except KeyError:
                try:
                    return self.outputs[item.lstrip('_')]
                except KeyError:
                    raise AttributeError('No I/O with name {} defined.'.format(item.lstrip('_')))
                # raise AttributeError('No Input with name {} defined.'.format(item.lstrip('_')))
        else:
            return super(Node, self).__getattr__(item)

    def getInputPin(self, inputName):
        """
        Returns a reference to the Pin instance associated with the input with the given name.
        :param inputName: str; Name of the input.
        :return: Pin instance
        :rtype: Pin
        """
        return self.inputPins[inputName]

    def getOutputPin(self, outputName):
        return self.outputPins[outputName]

    def getInputInfo(self, inputName):
        return self.inputs[inputName]

    def getOutputInfo(self, outputName):
        return self.outputs[outputName]

    def getInputID(self, inputName):
        return '{}:I{}'.format(self.ID, inputName)

    def getOutputID(self, outputName):
        return '{}:O{}'.format(self.ID, outputName)

    def getInputofType(self, varType):
        for inp in self.inputs.values():
            if issubclass(varType, inp.varType) or issubclass(inp.varType, varType):
                return inp

    def getOutputofType(self, varType):
        for out in self.outputs.values():
            if issubclass(varType, out.varType) or issubclass(out.varType, varType):
                return out

    def save(self):
        """
        Returns a dictionary containing all data necessary to reinstanciate the Node instance with the same properties
        it currently has. A list of the dictionaries of each node instance in a graph is all the data necessary to
        reinstanciate the whole graph.
        :return:
        """
        inputConns = [self.graph.getConnectionOfInput(inp) for inp in self.inputs.values()]
        # print(inputConns)
        inputConns = {inputConn['inputName']: inputConn['outputNode'].getOutputID(inputConn['outputName']) for inputConn in inputConns if inputConn}
        outputConns = {out.name: self.graph.getConnectionsOfOutput(out) for out in self.outputs.values()}
        for key, conns in outputConns.items():
            conns = [outputConn['inputNode'].getInputID(outputConn['inputName']) for outputConn in conns]
            outputConns[key] = conns
        return {'class': self.__class__.__name__,
                     'position': self.__pos__,
                     'inputs': [(inputName, inp.varType.__name__, inp(True), inp.default)
                                for inputName, inp in self.inputs.items()],
                     'inputConnections': inputConns,
                     'outputs': [(outputName, out.varType.__name__, out.value, out.default)
                                 for outputName, out in self.outputs.items()],
                     'outputConnections': outputConns}

    @classmethod
    def matchHint(cls, text: str):
        return cls.matchInputHint(text) or cls.matchOutputHint(text) or cls.matchClassTag(text)

    @classmethod
    def matchClassTag(cls, text: str):
        return any([tag.lower().startswith(text) for tag in cls.__tags__])

    @classmethod
    def matchInputHint(cls, text: str):
        if text == 'object':
            return True
        if any([any([hint.startswith(text) for hint in inp.hints]) for inp in cls.__inputs__.values()]):
            return True

    @classmethod
    def matchOutputHint(cls, text: str):
        if text == 'object':
            return True
        if any([any([hint.startswith(text) for hint in out.hints]) for out in cls.__outputs__.values()]):
            return True


class Pin(object):
    """
    Class for storing all information required to represent a input/output pin.
    """
    def __init__(self, pinID, info, node):
        self.ID = pinID
        self.name = info.name
        self.info = info
        info.ID = pinID
        self.node = node


@abstractNode
class ControlNode(Node):
    """
    Base class for nodes controlling the program flow e.g. If/Else constructs and loops.
    Control nodes have an additional control input and a finalize output.

    The control input is a special input that supports multiple input connections. For example a loop node gets
    notified of a finished iteration over its body by setting the input of the control input. If all iterations are
    completed, the last set input is passed to the finalize output.
    An If/Else construct uses the control input to notify the node that the selected branch terminated. When that
    happens, the value of the control input is set to the finalize output.

    Restricting the option to have multiple connections to ControlNodes only makes sure that the node responsible for
    branches in the execution tree is also the node responsible for putting the pieces back together.
    """
    Input('Start', object)
    Input('Control', object)
    Output('Final', object)

    def __init__(self, *args, **kwargs):
        super(ControlNode, self).__init__(*args, **kwargs)
        self.waiting = False




class SwitchNode(ControlNode):
    """
    Node for creating a basic if/else construction.
    The input 'Switch' accepts a bool. Depending of the value of the input, the 'True' or 'False' outputs are set to
    the value of the 'Start' input.
    As soon as the 'Control' input is set by one of the code branches originating from the 'True' and 'False' outputs,
    the value of the 'Final' output is set to the value of the 'Control' input.
    """
    Input('Switch', bool)
    Output('True', object)
    Output('False', object)

    def __init__(self, *args, **kwargs):
        super(SwitchNode, self).__init__(*args, **kwargs)
        self.fresh = True

    def check(self):
        if self.fresh:
            for inp in self.inputs.values():
                if inp.name == 'Control':
                    continue
                if not inp.isAvailable():
                    print('        {}: Prerequisites not met.'.format(str(self)))
                    return False
            return True
        else:
            if self.inputs['Control'].isAvailable():
                return True

    def run(self):
        print('Executing node {}'.format(self))
        if self.fresh:
            if self._Switch:
                self._True(self._Start)
            else:
                self._False(self._Start)
        else:
            self._Final(self._Control)

    def notify(self):
        if self.fresh:
            output = self.outputs['True'] if self._Switch else self.outputs['False']
            for con in self.graph.getConnectionsOfOutput(output):
                outputName = con['outputName']
                nextNode = con['inputNode']
                nextInput = con['inputName']
                nextNode.setInput(nextInput, self.outputs[outputName].value)
            self.fresh = False
            self.inputs['Start'].reset()
            self.inputs['Switch'].reset()
        else:
            output = self.outputs['Final']
            for con in self.graph.getConnectionsOfOutput(output):
                outputName = con['outputName']
                nextNode = con['inputNode']
                nextInput = con['inputName']
                nextNode.setInput(nextInput, self.outputs[outputName].value)
            self.fresh = True
        self.inputs['Control'].reset()


class Loop(ControlNode):
    """
    Generic loop node that iterates over a range(x: int)-like expression.
    """
    Input('Iterations', int)
    Output('LoopBody', object)

    def __init__(self, *args, **kwargs):
        super(ControlNode, self).__init__(*args, **kwargs)
        self.fresh = True
        self.counter = 0

    # def prepare(self):
    #     pass

    def check(self):
        if self.fresh:
            for inp in self.inputs.values():
                if inp.name == 'Control':
                    continue
                if not inp.isAvailable():
                    print('        {}: Prerequisites not met.'.format(str(self)))
                    return False
            return True
        if self.counter > 0:
            if self.inputs['Control'].isAvailable():
                return True

    def run(self):
        print('Executing node {}'.format(self))
        if self.fresh:
            self.counter = self._Iterations
            self._LoopBody(self._Start)
            self.fresh = False
        elif self.counter == 0:
            self._Final(self._Control)
        else:
            self.counter -= 1
            self._LoopBody(self._Control)


    def notify(self):
        if self.counter > 0:
            output = self.outputs['LoopBody']
            for con in self.graph.getConnectionsOfOutput(output):
                outputName = con['outputName']
                nextNode = con['inputNode']
                nextInput = con['inputName']
                # nextNode.prepare()
                nextNode.setInput(nextInput, self.outputs[outputName].value, override=True)
            self.inputs['Control'].reset()

        else:
            output = self.outputs['Final']
            for con in self.graph.getConnectionsOfOutput(output):
                outputName = con['outputName']
                nextNode = con['inputNode']
                nextInput = con['inputName']
                nextNode.setInput(nextInput, self.outputs[outputName].value)
            # self.prepare()
            self.fresh = True
            for inp in self.inputs.values():
                if not inp.name == 'Iterations':
                    inp.reset()
        # print(self.inProgress)
        # exit()


class WaitAll(Node):
    """
    Watis for all inputs to be set before executing further nodes.
    """
    Input('1', object)
    Input('2', object)
    Output('out', object)

    def notify(self):
        super(WaitAll, self).notify()
        [inp.reset() for inp in self.inputs.values()]


class WaitAny(WaitAll):
    """
    Waits for any inputs to be set. This doesn't make much sense, does it?
    """

    def check(self):
        for inp in self.inputs.values():
            if inp.valueSet:
                print('        {}: Prerequisites not met.'.format(str(self)))
                return True

    def run(self):
        super(WaitAny, self).run()
        for inp in self.inputs.values():
            if inp.valueSet:
                self._out(inp.value)


class Test(Node):
    Input('Test', bool)
    Output('T', bool)

    def run(self):
        super(Test, self).run()
        print(self._Test)
        self._T(self._Test)


class TestNode(Node):
    Input('strInput', str)
    Output('strOutput', str)


class FinalTestNode(TestNode):
    pass


class TestNode2(Node):
    Input('strInput', str)
    Input('floatInput', float, default=10.)
    Input('Input', str, default='TestNode')
    Output('strOutput', str)


class CreateBool(Node):
    """
    Creates a Boolean.
    """
    Input('Value', bool, select=(True, False))
    Output('Boolean', bool)

    def run(self):
        super(CreateBool, self).run()
        self._Boolean(self._Value)


class CreateInt(Node):
    """
    Creates an Integer.
    """
    Input('Value', int, )
    Output('Integer', int)
    def run(self):
        super(CreateInt, self).run()
        self._Integer(self._Value)


class ReadNode(Node):
    """
    Node for reading a string from a file.
    """
    Input('Name', str)
    Output('Content', str)

    def run(self):
        super(ReadNode, self).run()
        fileName = self._Name
        try:
            with open(fileName, 'r') as fp:
                c = fp.read()
        except IOError:
            self.raiseError('IOError', 'No file named {}.'.format(fileName))
            return 1
        self._Content(c)


class ForEach(ControlNode):
    """
    Generic loop node that iterates over all elements in a list.
    """
    Input('Start', object, list=True)
    Output('ListElement', object)

    def __init__(self, *args, **kwargs):
        super(ForEach, self).__init__(*args, **kwargs)
        self.fresh = True
        self.counter = 0
        self.done = False

    def check(self):
        if self.fresh:
            for inp in self.inputs.values():
                if inp.name == 'Control':
                    continue
                if not inp.isAvailable():
                    print('        {}: Prerequisites not met.'.format(str(self)))
                    return False
            return True
        else:
            if self.inputs['Control'].isAvailable():
                return True

    def run(self):
        super(ForEach, self).run()
        self.fresh = False
        try:
            self._ListElement(self._Start[self.counter])
        except IndexError:
            self._Final(self._Start)
            self.done = True
        self.counter += 1

    def notify(self):
        if not self.done:
            output = self.outputs['ListElement']
            for con in self.graph.getConnectionsOfOutput(output):
                outputName = con['outputName']
                nextNode = con['inputNode']
                nextInput = con['inputName']
                # nextNode.prepare()
                nextNode.setInput(nextInput, self.outputs[outputName].value, override=True)
            self.inputs['Control'].reset()

        else:
            output = self.outputs['Final']
            for con in self.graph.getConnectionsOfOutput(output):
                outputName = con['outputName']
                nextNode = con['inputNode']
                nextInput = con['inputName']
                nextNode.setInput(nextInput, self.outputs[outputName].value)
            # self.prepare()
            self.fresh = True
            for inp in self.inputs.values():
                if not inp.name == 'Iterations':
                    inp.reset()
            self.counter = 0
            self.fresh = True
            self.done = False


class IsEqual(Node):
    """
    Sets output to object1 == object2.
    """
    Input('object1', object)
    Input('object2', object)
    Output('Equal', bool)

    def run(self):
        super(IsEqual, self).run()
        self._Equal(self._object1 == self._object2)


class CreateString(Node):
    """
    Creates a string object.
    """
    Input('Str', str)
    Output('String', str)

    def run(self):
        super(CreateString, self).run()
        self._String(self._Str)


@abstractNode
class DebugNode(Node):
    """
    Subclass this node for creating custom nodes related to debugging a graph.
    """
    Tag('Debug')

    def print(self, *args):
        string = ' '.join(args)
        print('[DEBUG]', string)


class DebugPrint(DebugNode):
    """
    Prints node instance specific debugging information to the cmd line. The input is than passed on straight to
    the output without manipulating the object.
    Custom debug information can be specified in an objects corresponding floppy.types.Type subclass.
    """
    Input('Object', object)
    Output('Out', object)

    def run(self):
        super(DebugPrint, self).run()
        obj = self._Object
        try:
            self.print(str(obj.__FloppyType__.debugInfoGetter(obj)()))
        except AttributeError:
            self.print(str(obj))
        self._Out(obj)





# TODO Cleanup this mess. Prepare method and probably a lot of other stuff is no longer needed.
