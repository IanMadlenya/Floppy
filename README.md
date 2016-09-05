# Floppy
Flowchart Python -- A multipurpose Python node editor.

![Example Graph](/floppy/ressources/img.png?raw=true "Graph Example")

Floppy includes a PyQt5 based graphical editor for creating graphs consisting of logically connected nodes.
Floppy also provides an interpreter for these graphs that can run on a remote machine and is controlled via TCP/IP.

A recently added feature is the automatic concurrent execution of graphs. The Graph Interpreter will continuously check
which nodes are ready to be executed and will then create a new thread for running each node.

To execute a graph, the 'Run' button can be pressed.
This causes the editor to spawn a local graph interpreter (equivalent to pressing 'Spawn'), to push the graph to the
interpreter (equivalent to pressing 'Push') and then to unpause the interpreter (equivalent to pressing 'Unpause').


A main design goal is to make the addition of custom nodes as easy as possible. For example the following code will
make a node for adding two integer available in the editor:


    class AddIntergers(Node):
        Input('Integer1', int)
        Input('Integer2', int)
        Output('Sum', int)

    def run():
        self._Sum(self._Integer1 + self._Integer2)


While most IDEs will complain about the code the Node class's meta class takes care of making the objects 'Input' and
'Output' available in the class's scope. The meta class will also make sure the editor itself is aware of the newly
defined node class.
Every defined input can be accessed either by using 'self.\_\<InputName\>' or by using 'self.inputs['\<InputName\>']''.
Outputs are set by calling the 'self.\_\<OutputName\>(\<value\>)' object with the new value as argument.

By default any custom node will wait for all inputs to be set before trying to execute a node. If a more sophisticated
check is required, the 'Node.check()' method can be overridden.

After executing a node the node's 'notify()' method is called to notify all connected nodes about possible changes to
the inputs they are waiting for. Custom post-execution behavior can be implemented here.

##How To Create a Custom Node Step by Step
In order to use Floppy, a Python interpreter compatible with PyQt5 is required. This probably means Python3.4 is needed.
To use the dynamic plotting nodes, matplotlib with all its dependencies is required. However, Floppy will still work as
long as no plotting nodes are used.

Setup: Add the cloned directory to your PYTHONPATH environment variable.
Check if you can import 'floppy' in your Python3 console

1. Create a new \<FileName\>.py file in the 'CustomNodes' subdirectory. This directory is automatically scanned for 
custom nodes. Creating a new file prevents conflicts when pulling updates from Github.

2. Start the file with importing the following objects:
```python
    from floppy.node import Node, Input, Output, Tag, abstractNode
```

3. Create your custom Node. (MyNode in this case)
```python
    class MyNode(Node):
        pass
```
If the editor is started now the custom node class will be available in the list at the top-right widget.

4. Define inputs and outputs.
```python
    class MyNode(Node):
        Input('MyInput1', str)
        Input('MyInput2', float, list=True)
        Output('MyOutput1', int)
        Output('MyOutput2', bool)
```    
This will create two inputs and two outputs of the type defined by the second argument. The optional 'list' argument indicates
that a list of the appropriate type is expected. This will be visualized by a square icon instead of a circle one.
The first argument - the Input/Output name - can be any legal Python variable name and must be unique within the scope of a Node class.

5. Define the execution behavior by overriding the 'run()' method.
```python
    class MyNode(Node):
        ...
         def run(self):
            super(MyNode, self).run()
            self._MyInput1 # is a reference to the accordingly named input. The object will have the appropriate type.
            self._MyInput2 # is a reference to the accordingly named input. The object will have the appropriate type.
            self._MyOutput1(1) # will set the value of the output with the corresponding name to 1. The type must match.
            self._MyOutput1(True) # will set the value of the output with the corresponding name to True. The type must match.
```
Within the body of the 'run' method any legal Python3 code can be executed. Keep in mind that the method will most likely be executed
in a seperate thread. To get the most out of that feature it is recommended to use subprocesses and/or C-library calls whenever reasonable.
The call of the parent class's implementation is recommended but not necessary. This may change in the future.

6. The node should work now. Keep in mind that all outputs that are not set within the 'run' method's scope will have the value 'None'.
Several ways to further customize nodes will be discussed next but will be unnecessary for most applications.

7. Customize when a node is executed. 
```python
    class MyNode(Node):
        ...
        def check(self):
            for inp in self.inputs.values():
                if not inp.isAvailable():
                    return False
            return True
```
This is the default implementation that can be adjusted according to personal needs.
For example a time.sleep('...') can be used in combination with probing a file to continously watch a file and
analyze data streams put out by other applications.

8. Initialize custom properties.
```python
    class MyNode(Node):
        ...
        def setup(self):
            self.myCustomAttribute
```
This method is called after \__init\__ was executed. This is simply a convenient way to
avoid annoying calls of super(MyNode, self).\__init\__(*args, **kwargs).

9. Custom notification bahavior.
```python
    class MyNode(Node):
        ...
        def notify(self):
            ...
```
This method will be called after the 'run' method was executed. The method is responsible for
transferring the output values of the custom node to the inputs of the nodes connected to it.
The custom implementation looks rather confusing and will not be discussed here.
The default implementation can be checked in the base class's implementation.
An example for custom behavior that leads to branches similar to if/else constructs can be 
seen in the 'Switch' node which is also found in the floppy.node module.
Another non-standard behavior can be observed in the case of the ForEach node.

10. Custom report behavior.
```python
    class MyNode(Node):
        ...
        def report(self):
            r = super(MyNode, self).report()
            r['template'] = 'myCustomTemplate
            ...
            return r 
```
The 'report' method is called by the editor-interpreter interface whenever
a report about the nodes current status is requested by the editor. The reports
are based on HTML templates. Look at the reportWidget module and templates module
for details. However, keep in mind that the system will most likely change in the
future.